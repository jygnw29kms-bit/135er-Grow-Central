using System.Globalization;
using System.IO.Compression;
using System.Text;
using Microsoft.Data.Sqlite;

public sealed class CatalogStore
{
    private readonly string _dbPath;
    private readonly SemaphoreSlim _writeLock = new(1, 1);
    private static readonly CultureInfo De = CultureInfo.GetCultureInfo("de-DE");

    public CatalogStore()
    {
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
        var root = Environment.GetEnvironmentVariable("WM_CATALOG_DATA");
        if (string.IsNullOrWhiteSpace(root))
            root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "WorkshopManager");
        Directory.CreateDirectory(root);
        _dbPath = Path.Combine(root, "supplier-catalog.sqlite");
        Initialize();
    }

    private SqliteConnection Open()
    {
        var cn = new SqliteConnection($"Data Source={_dbPath};Cache=Shared");
        cn.Open();
        using var pragma = cn.CreateCommand();
        pragma.CommandText = "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA temp_store=MEMORY;";
        pragma.ExecuteNonQuery();
        return cn;
    }

    private void Initialize()
    {
        using var cn = Open();
        using var cmd = cn.CreateCommand();
        cmd.CommandText = """
        CREATE TABLE IF NOT EXISTS catalog_meta(
          tenant_id TEXT NOT NULL, source TEXT NOT NULL, source_name TEXT NOT NULL,
          imported_at TEXT NOT NULL, record_count INTEGER NOT NULL, data_date TEXT NULL,
          PRIMARY KEY(tenant_id, source)
        );
        CREATE TABLE IF NOT EXISTS kba_vehicle(
          id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL, kba_no TEXT NOT NULL,
          hsn TEXT NOT NULL, tsn TEXT NOT NULL, manufacturer TEXT, model TEXT, type_name TEXT,
          kw INTEGER, ps INTEGER, ccm INTEGER, build_from TEXT, build_to TEXT, fuel TEXT,
          engine_type TEXT, body TEXT, drive TEXT, gearbox TEXT, cylinders INTEGER,
          ktyp_no TEXT, manufacturer_no TEXT, model_no TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_kba_tenant_kba ON kba_vehicle(tenant_id,kba_no);
        CREATE INDEX IF NOT EXISTS ix_kba_tenant_hsn_tsn ON kba_vehicle(tenant_id,hsn,tsn);
        CREATE INDEX IF NOT EXISTS ix_kba_tenant_make_model ON kba_vehicle(tenant_id,manufacturer,model);

        CREATE TABLE IF NOT EXISTS aag_article(
          id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL,
          art_nr TEXT, art_nr_compact TEXT, hennig_art_nr TEXT, description1 TEXT, description2 TEXT,
          usage_no TEXT, replacement_note TEXT, gross_price REAL, gross_valid_from TEXT,
          purchase_discount REAL, purchase_price REAL, article_group TEXT, price_unit REAL,
          net_indicator TEXT, core_indicator TEXT, core_value REAL, supplier_no TEXT,
          successor_hennig TEXT, successor_original TEXT, ean TEXT, article_status TEXT,
          brand_description TEXT, brand TEXT, weight REAL, unit TEXT, tme TEXT, created_at_source TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_aag_tenant_art ON aag_article(tenant_id,art_nr);
        CREATE INDEX IF NOT EXISTS ix_aag_tenant_artcompact ON aag_article(tenant_id,art_nr_compact);
        CREATE INDEX IF NOT EXISTS ix_aag_tenant_hennig ON aag_article(tenant_id,hennig_art_nr);
        CREATE INDEX IF NOT EXISTS ix_aag_tenant_ean ON aag_article(tenant_id,ean);
        CREATE INDEX IF NOT EXISTS ix_aag_tenant_brand ON aag_article(tenant_id,brand);
        CREATE INDEX IF NOT EXISTS ix_aag_tenant_successor ON aag_article(tenant_id,successor_original);
        """;
        cmd.ExecuteNonQuery();
    }

    public async Task<object> StatusAsync(Guid tenantId, CancellationToken ct)
    {
        EnsureDemoSeed(tenantId);
        using var cn = Open();
        var meta = new List<object>();
        using (var cmd = cn.CreateCommand())
        {
            cmd.CommandText = "SELECT source,source_name,imported_at,record_count,data_date FROM catalog_meta WHERE tenant_id=$t ORDER BY source";
            cmd.Parameters.AddWithValue("$t", tenantId.ToString());
            using var r = await cmd.ExecuteReaderAsync(ct);
            while (await r.ReadAsync(ct))
                meta.Add(new {
                    source = r.GetString(0), sourceName = r.GetString(1),
                    importedAt = r.GetString(2), recordCount = r.GetInt64(3),
                    dataDate = r.IsDBNull(4) ? null : r.GetString(4)
                });
        }
        return new {
            sources = meta,
            suppliedFiles = new {
                kba = new { file = "KBA.ZIP", sourceRecords = 120833, sourceDate = "03.08.2026" },
                aag = new { file = "NeuePreisdatein.csv", sourceRecords = 1190235, columns = 27, monthlyUpdate = true }
            }
        };
    }

    public async Task<List<Dictionary<string, object?>>> SearchKbaAsync(Guid tenantId, string? hsn, string? tsn, string? q, int limit, CancellationToken ct)
    {
        EnsureDemoSeed(tenantId);
        limit = Math.Clamp(limit, 1, 100);
        var h = (hsn ?? "").Trim().ToUpperInvariant();
        var t = (tsn ?? "").Trim().ToUpperInvariant();
        var s = (q ?? "").Trim();
        using var cn = Open();
        using var cmd = cn.CreateCommand();
        cmd.CommandText = """
        SELECT kba_no,hsn,tsn,manufacturer,model,type_name,kw,ps,ccm,build_from,build_to,fuel,engine_type,body,drive,gearbox,cylinders,ktyp_no,manufacturer_no,model_no
        FROM kba_vehicle
        WHERE tenant_id=$tenant
          AND ($hsn='' OR hsn=$hsn)
          AND ($tsn='' OR tsn LIKE $tsn || '%')
          AND ($q='' OR manufacturer LIKE $qp OR model LIKE $qp OR type_name LIKE $qp OR kba_no LIKE $qp)
        ORDER BY manufacturer,model,type_name LIMIT $limit
        """;
        cmd.Parameters.AddWithValue("$tenant", tenantId.ToString());
        cmd.Parameters.AddWithValue("$hsn", h);
        cmd.Parameters.AddWithValue("$tsn", t);
        cmd.Parameters.AddWithValue("$q", s);
        cmd.Parameters.AddWithValue("$qp", s + "%");
        cmd.Parameters.AddWithValue("$limit", limit);
        using var r = await cmd.ExecuteReaderAsync(ct);
        var rows = new List<Dictionary<string, object?>>();
        while (await r.ReadAsync(ct))
        {
            rows.Add(new Dictionary<string, object?> {
                ["kbaNo"]=r.GetString(0),["hsn"]=r.GetString(1),["tsn"]=r.GetString(2),
                ["manufacturer"]=Val(r,3),["model"]=Val(r,4),["type"]=Val(r,5),
                ["kw"]=IntVal(r,6),["ps"]=IntVal(r,7),["ccm"]=IntVal(r,8),
                ["buildFrom"]=Val(r,9),["buildTo"]=Val(r,10),["fuel"]=Val(r,11),
                ["engineType"]=Val(r,12),["body"]=Val(r,13),["drive"]=Val(r,14),
                ["gearbox"]=Val(r,15),["cylinders"]=IntVal(r,16),["ktypNo"]=Val(r,17),
                ["manufacturerNo"]=Val(r,18),["modelNo"]=Val(r,19)
            });
        }
        return rows;
    }

    public async Task<List<Dictionary<string, object?>>> SearchAagAsync(Guid tenantId, string? q, string? brand, string? status, int limit, CancellationToken ct)
    {
        EnsureDemoSeed(tenantId);
        limit = Math.Clamp(limit, 1, 100);
        var s = (q ?? "").Trim();
        var compact = new string(s.Where(char.IsLetterOrDigit).ToArray()).ToUpperInvariant();
        using var cn = Open();
        using var cmd = cn.CreateCommand();
        cmd.CommandText = """
        SELECT art_nr,art_nr_compact,hennig_art_nr,description1,description2,gross_price,gross_valid_from,
               purchase_discount,purchase_price,article_group,core_value,supplier_no,successor_hennig,
               successor_original,ean,article_status,brand,weight,unit,created_at_source
        FROM aag_article
        WHERE tenant_id=$tenant
          AND ($q='' OR art_nr=$q OR art_nr_compact=$compact OR hennig_art_nr=$q OR ean=$q OR
               successor_original=$q OR art_nr LIKE $qp OR description1 LIKE $qp OR brand LIKE $qp)
          AND ($brand='' OR brand=$brand)
          AND ($status='' OR article_status=$status)
        ORDER BY CASE WHEN art_nr=$q OR art_nr_compact=$compact OR hennig_art_nr=$q OR ean=$q THEN 0 ELSE 1 END,
                 brand,art_nr
        LIMIT $limit
        """;
        cmd.Parameters.AddWithValue("$tenant", tenantId.ToString());
        cmd.Parameters.AddWithValue("$q", s);
        cmd.Parameters.AddWithValue("$compact", compact);
        cmd.Parameters.AddWithValue("$qp", s + "%");
        cmd.Parameters.AddWithValue("$brand", (brand ?? "").Trim());
        cmd.Parameters.AddWithValue("$status", (status ?? "").Trim());
        cmd.Parameters.AddWithValue("$limit", limit);
        using var r = await cmd.ExecuteReaderAsync(ct);
        var rows = new List<Dictionary<string, object?>>();
        while (await r.ReadAsync(ct))
        {
            rows.Add(new Dictionary<string, object?> {
                ["artNr"]=Val(r,0),["artNrCompact"]=Val(r,1),["hennigArtNr"]=Val(r,2),
                ["description1"]=Val(r,3),["description2"]=Val(r,4),["grossPrice"]=DecVal(r,5),
                ["grossValidFrom"]=Val(r,6),["purchaseDiscount"]=DecVal(r,7),["purchasePrice"]=DecVal(r,8),
                ["articleGroup"]=Val(r,9),["coreValue"]=DecVal(r,10),["supplierNo"]=Val(r,11),
                ["successorHennig"]=Val(r,12),["successorOriginal"]=Val(r,13),["ean"]=Val(r,14),
                ["articleStatus"]=Val(r,15),["brand"]=Val(r,16),["weight"]=DecVal(r,17),
                ["unit"]=Val(r,18),["sourceCreatedAt"]=Val(r,19)
            });
        }
        return rows;
    }

    public async Task<object> ImportAagAsync(Guid tenantId, Stream stream, string sourceName, CancellationToken ct)
    {
        await _writeLock.WaitAsync(ct);
        try
        {
            using var cn = Open();
            using var tx = cn.BeginTransaction();
            using (var del = cn.CreateCommand())
            {
                del.Transaction = tx;
                del.CommandText = "DELETE FROM aag_article WHERE tenant_id=$t; DELETE FROM catalog_meta WHERE tenant_id=$t AND source='AAG';";
                del.Parameters.AddWithValue("$t", tenantId.ToString());
                await del.ExecuteNonQueryAsync(ct);
            }

            using var reader = new StreamReader(stream, new UTF8Encoding(false), true, 1024 * 128, leaveOpen: true);
            var headerLine = await reader.ReadLineAsync(ct) ?? throw new InvalidDataException("AAG-Datei ist leer.");
            var headers = ParseCsvLine(headerLine);
            var map = headers.Select((x,i)=>(x,i)).ToDictionary(x=>x.x, x=>x.i, StringComparer.OrdinalIgnoreCase);

            using var ins = cn.CreateCommand();
            ins.Transaction = tx;
            ins.CommandText = """
            INSERT INTO aag_article(tenant_id,art_nr,art_nr_compact,hennig_art_nr,description1,description2,usage_no,replacement_note,
              gross_price,gross_valid_from,purchase_discount,purchase_price,article_group,price_unit,net_indicator,core_indicator,core_value,
              supplier_no,successor_hennig,successor_original,ean,article_status,brand_description,brand,weight,unit,tme,created_at_source)
            VALUES($tenant,$art,$compact,$hennig,$d1,$d2,$usage,$replacement,$gross,$grossfrom,$discount,$purchase,$group,$priceunit,
              $net,$coreind,$core,$supplier,$succH,$succO,$ean,$status,$branddesc,$brand,$weight,$unit,$tme,$created)
            """;
            foreach (var p in new[]{"tenant","art","compact","hennig","d1","d2","usage","replacement","gross","grossfrom","discount","purchase","group","priceunit","net","coreind","core","supplier","succH","succO","ean","status","branddesc","brand","weight","unit","tme","created"})
                ins.Parameters.Add(new SqliteParameter("$"+p, null));

            long count = 0;
            string? line;
            while ((line = await reader.ReadLineAsync(ct)) is not null)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                var v = ParseCsvLine(line);
                string G(string name) => map.TryGetValue(name, out var i) && i < v.Count ? v[i].Trim() : "";
                ins.Parameters["$tenant"].Value = tenantId.ToString();
                ins.Parameters["$art"].Value = G("ArtNr"); ins.Parameters["$compact"].Value = G("ArtNrKomp");
                ins.Parameters["$hennig"].Value = G("HennigArtNr"); ins.Parameters["$d1"].Value = G("Bez1"); ins.Parameters["$d2"].Value = G("Bez2");
                ins.Parameters["$usage"].Value = G("GebrauchsNr"); ins.Parameters["$replacement"].Value = G("ErsatzHinweis");
                ins.Parameters["$gross"].Value = ParseDecimal(G("BruttoPreis")); ins.Parameters["$grossfrom"].Value = G("BruttoGueltigAb");
                ins.Parameters["$discount"].Value = ParseDecimal(G("Einkaufsrabatt")); ins.Parameters["$purchase"].Value = ParseDecimal(G("EinkaufsPreis"));
                ins.Parameters["$group"].Value = G("ArtikelGruppe"); ins.Parameters["$priceunit"].Value = ParseDecimal(G("Preiseinheit"));
                ins.Parameters["$net"].Value = G("Nettokennzeichen"); ins.Parameters["$coreind"].Value = G("Altteilkennzeichen");
                ins.Parameters["$core"].Value = ParseDecimal(G("Pfandwert")); ins.Parameters["$supplier"].Value = G("LieferantenNr");
                ins.Parameters["$succH"].Value = G("NachfolgeNummerHennig"); ins.Parameters["$succO"].Value = G("NachfolgeNummerOriginal");
                ins.Parameters["$ean"].Value = G("Ean"); ins.Parameters["$status"].Value = G("Artikelstatus");
                ins.Parameters["$branddesc"].Value = G("MarkeBez1"); ins.Parameters["$brand"].Value = G("Marke");
                ins.Parameters["$weight"].Value = ParseDecimal(G("Gewicht")); ins.Parameters["$unit"].Value = G("Mengeneinheit");
                ins.Parameters["$tme"].Value = G("TME"); ins.Parameters["$created"].Value = G("Erstellt_am");
                await ins.ExecuteNonQueryAsync(ct);
                count++;
            }
            await WriteMeta(cn, tx, tenantId, "AAG", sourceName, count, null, ct);
            await tx.CommitAsync(ct);
            return new { source="AAG", imported=count, sourceName };
        }
        finally { _writeLock.Release(); }
    }

    public async Task<object> ImportKbaZipAsync(Guid tenantId, Stream zipStream, string sourceName, CancellationToken ct)
    {
        await _writeLock.WaitAsync(ct);
        try
        {
            using var archive = new ZipArchive(zipStream, ZipArchiveMode.Read, leaveOpen: true);
            var entry = archive.Entries.FirstOrDefault(x => x.Name.Equals("kba.dbf", StringComparison.OrdinalIgnoreCase))
                ?? throw new InvalidDataException("kba.dbf wurde im ZIP nicht gefunden.");
            using var cn = Open();
            using var tx = cn.BeginTransaction();
            using (var del = cn.CreateCommand())
            {
                del.Transaction = tx;
                del.CommandText = "DELETE FROM kba_vehicle WHERE tenant_id=$t; DELETE FROM catalog_meta WHERE tenant_id=$t AND source='KBA';";
                del.Parameters.AddWithValue("$t", tenantId.ToString());
                await del.ExecuteNonQueryAsync(ct);
            }

            using var dbf = entry.Open();
            var header = new byte[32];
            await ReadExact(dbf, header, ct);
            var recordCount = BitConverter.ToUInt32(header, 4);
            var headerLength = BitConverter.ToUInt16(header, 8);
            var recordLength = BitConverter.ToUInt16(header, 10);
            var fieldBytes = new byte[headerLength - 32];
            await ReadExact(dbf, fieldBytes, ct);
            var fields = new List<DbfField>();
            for (var p=0; p+32<=fieldBytes.Length && fieldBytes[p]!=0x0D; p+=32)
            {
                var name = Encoding.ASCII.GetString(fieldBytes, p, 11).TrimEnd('\0',' ');
                fields.Add(new DbfField(name, fieldBytes[p+11], fieldBytes[p+16]));
            }
            var fieldMap = fields.Select((f,i)=>(f,i)).ToDictionary(x=>x.f.Name, x=>x.i, StringComparer.OrdinalIgnoreCase);
            using var ins = cn.CreateCommand();
            ins.Transaction = tx;
            ins.CommandText = """
            INSERT INTO kba_vehicle(tenant_id,kba_no,hsn,tsn,manufacturer,model,type_name,kw,ps,ccm,build_from,build_to,
              fuel,engine_type,body,drive,gearbox,cylinders,ktyp_no,manufacturer_no,model_no)
            VALUES($tenant,$kba,$hsn,$tsn,$make,$model,$type,$kw,$ps,$ccm,$from,$to,$fuel,$engine,$body,$drive,$gear,$cyl,$ktyp,$kher,$kmod)
            """;
            foreach (var p in new[]{"tenant","kba","hsn","tsn","make","model","type","kw","ps","ccm","from","to","fuel","engine","body","drive","gear","cyl","ktyp","kher","kmod"})
                ins.Parameters.Add(new SqliteParameter("$"+p, null));

            var rec = new byte[recordLength];
            long imported = 0;
            for (long row=0; row<recordCount; row++)
            {
                await ReadExact(dbf, rec, ct);
                if (rec[0] == 0x2A) continue;
                var values = new string[fields.Count];
                var pos=1;
                for (var i=0;i<fields.Count;i++)
                {
                    var f=fields[i];
                    values[i]=f.Type=='M' ? "" : Encoding.GetEncoding(1252).GetString(rec,pos,f.Length).Trim();
                    pos+=f.Length;
                }
                string G(string name) => fieldMap.TryGetValue(name,out var i) ? values[i] : "";
                var kba=G("KBANR").ToUpperInvariant();
                if (kba.Length < 5) continue;
                ins.Parameters["$tenant"].Value=tenantId.ToString(); ins.Parameters["$kba"].Value=kba;
                ins.Parameters["$hsn"].Value=kba[..Math.Min(4,kba.Length)];
                ins.Parameters["$tsn"].Value=kba.Length>4?kba[4..]:"";
                ins.Parameters["$make"].Value=G("HERSTELLER"); ins.Parameters["$model"].Value=G("MODELL"); ins.Parameters["$type"].Value=G("TYP");
                ins.Parameters["$kw"].Value=ParseInt(G("KW")); ins.Parameters["$ps"].Value=ParseInt(G("PS")); ins.Parameters["$ccm"].Value=ParseInt(G("CCM"));
                ins.Parameters["$from"].Value=G("CBJVON"); ins.Parameters["$to"].Value=G("CBJBIS");
                ins.Parameters["$fuel"].Value=G("BEZKRST"); ins.Parameters["$engine"].Value=G("BEZMOTART"); ins.Parameters["$body"].Value=G("BEZAUFBAU");
                ins.Parameters["$drive"].Value=G("BEZANTR"); ins.Parameters["$gear"].Value=G("BEZGETR"); ins.Parameters["$cyl"].Value=ParseInt(G("ZYL"));
                ins.Parameters["$ktyp"].Value=G("KTYPNR"); ins.Parameters["$kher"].Value=G("KHERNR"); ins.Parameters["$kmod"].Value=G("KMODNR");
                await ins.ExecuteNonQueryAsync(ct);
                imported++;
            }
            await WriteMeta(cn, tx, tenantId, "KBA", sourceName, imported, "03.08.2026", ct);
            await tx.CommitAsync(ct);
            return new { source="KBA", imported, sourceName, dataDate="03.08.2026" };
        }
        finally { _writeLock.Release(); }
    }

    private void EnsureDemoSeed(Guid tenantId)
    {
        using var cn=Open();
        using var check=cn.CreateCommand();
        check.CommandText="SELECT COUNT(*) FROM catalog_meta WHERE tenant_id=$t";
        check.Parameters.AddWithValue("$t",tenantId.ToString());
        if (Convert.ToInt64(check.ExecuteScalar())>0) return;
        using var tx=cn.BeginTransaction();

        var kbas = new[]{
            new[]{"0035AFR","OPEL","CORSA D (S07)","1.4 (L08, L68)","66","90","1364","07.2006","08.2014","Benzin","Otto","Schrägheck","Frontantrieb","4"},
            new[]{"0603AXS","VW","PASSAT B7 (362)","1.4 TSI","","","","","","","","","",""},
            new[]{"8566AUG","FORD","C-MAX II (DXA/CB7, DXA/CEU)","1.6 Ti","92","125","1596","12.2010","06.2019","Benzin","Otto","Großraumlimousine","Frontantrieb","4"},
            new[]{"0005381","BMW","1502-2002 (E10)","1502","55","75","1573","01.1975","07.1977","Benzin","Otto","Stufenheck","Heckantrieb","4"},
            new[]{"0600469","AUDI","50 (863)","1.1","37","50","1093","08.1974","07.1978","Benzin","Otto","Schrägheck","Frontantrieb","4"},
            new[]{"0009320","MERCEDES-BENZ","PONTON (W120)","180 D (120.110)","32","44","1770","01.1953","07.1959","Diesel","Diesel","Stufenheck","Heckantrieb","4"}
        };
        foreach(var x in kbas)
        {
            using var c=cn.CreateCommand(); c.Transaction=tx;
            c.CommandText = "INSERT INTO kba_vehicle(tenant_id,kba_no,hsn,tsn,manufacturer,model,type_name,kw,ps,ccm,build_from,build_to,fuel,engine_type,body,drive,cylinders) " +
                            "VALUES($t,$k,$h,$s,$m,$mo,$ty,$kw,$ps,$ccm,$bf,$bt,$f,$e,$b,$d,$z)";
            c.Parameters.AddWithValue("$t",tenantId.ToString()); c.Parameters.AddWithValue("$k",x[0]); c.Parameters.AddWithValue("$h",x[0][..4]); c.Parameters.AddWithValue("$s",x[0][4..]);
            c.Parameters.AddWithValue("$m",x[1]);c.Parameters.AddWithValue("$mo",x[2]);c.Parameters.AddWithValue("$ty",x[3]);
            c.Parameters.AddWithValue("$kw",ParseInt(x[4]));c.Parameters.AddWithValue("$ps",ParseInt(x[5]));c.Parameters.AddWithValue("$ccm",ParseInt(x[6]));
            c.Parameters.AddWithValue("$bf",x[7]);c.Parameters.AddWithValue("$bt",x[8]);c.Parameters.AddWithValue("$f",x[9]);c.Parameters.AddWithValue("$e",x[10]);
            c.Parameters.AddWithValue("$b",x[11]);c.Parameters.AddWithValue("$d",x[12]);c.Parameters.AddWithValue("$z",ParseInt(x[13]));c.ExecuteNonQuery();
        }

        var aag = new[]{
            new[]{"8710-29203","871029203","100000606","GASFEDER FUER HECKKLAPPE","23.80","10.95","108","103357018","6054BG","5709147164839","ABVERKAUF-AAG","TRISCAN"},
            new[]{"130000","130000","100011965","Rad 6½Jx16 Alcar Hybr. Golf5","84.00","73.92","1992","","","9008071300006","AKTIV-BESTELL","ALCAR"},
            new[]{"130001","130001","100011966","Rad 6½Jx16 Alcar Hybr. Audi/VW","84.00","73.92","1992","","","9008071300013","AKTIV-BESTELL","ALCAR"}
        };
        foreach(var x in aag)
        {
            using var c=cn.CreateCommand(); c.Transaction=tx;
            c.CommandText = "INSERT INTO aag_article(tenant_id,art_nr,art_nr_compact,hennig_art_nr,description1,gross_price,purchase_price,supplier_no,successor_hennig,successor_original,ean,article_status,brand,unit) " +
                            "VALUES($t,$a,$ac,$h,$d,$g,$p,$s,$sh,$so,$e,$st,$b,'Stück')";
            c.Parameters.AddWithValue("$t",tenantId.ToString());c.Parameters.AddWithValue("$a",x[0]);c.Parameters.AddWithValue("$ac",x[1]);c.Parameters.AddWithValue("$h",x[2]);
            c.Parameters.AddWithValue("$d",x[3]);c.Parameters.AddWithValue("$g",decimal.Parse(x[4],CultureInfo.InvariantCulture));c.Parameters.AddWithValue("$p",decimal.Parse(x[5],CultureInfo.InvariantCulture));
            c.Parameters.AddWithValue("$s",x[6]);c.Parameters.AddWithValue("$sh",x[7]);c.Parameters.AddWithValue("$so",x[8]);c.Parameters.AddWithValue("$e",x[9]);c.Parameters.AddWithValue("$st",x[10]);c.Parameters.AddWithValue("$b",x[11]);c.ExecuteNonQuery();
        }
        WriteMetaSync(cn,tx,tenantId,"KBA","KBA.ZIP · Demoauszug",kbas.Length,"03.08.2026");
        WriteMetaSync(cn,tx,tenantId,"AAG","NeuePreisdatein.csv · Demoauszug",aag.Length,null);
        tx.Commit();
    }

    private static async Task WriteMeta(SqliteConnection cn, SqliteTransaction tx, Guid tenant, string source, string name, long count, string? date, CancellationToken ct)
    {
        using var c=cn.CreateCommand();c.Transaction=tx;c.CommandText =
            "INSERT INTO catalog_meta(tenant_id,source,source_name,imported_at,record_count,data_date) " +
            "VALUES($t,$s,$n,$i,$c,$d) ON CONFLICT(tenant_id,source) DO UPDATE SET " +
            "source_name=excluded.source_name,imported_at=excluded.imported_at,record_count=excluded.record_count,data_date=excluded.data_date";
        c.Parameters.AddWithValue("$t",tenant.ToString());c.Parameters.AddWithValue("$s",source);c.Parameters.AddWithValue("$n",name);c.Parameters.AddWithValue("$i",DateTimeOffset.UtcNow.ToString("O"));
        c.Parameters.AddWithValue("$c",count);c.Parameters.AddWithValue("$d",(object?)date??DBNull.Value);await c.ExecuteNonQueryAsync(ct);
    }
    private static void WriteMetaSync(SqliteConnection cn, SqliteTransaction tx, Guid tenant, string source, string name, long count, string? date)
    {
        using var c=cn.CreateCommand();c.Transaction=tx;c.CommandText="INSERT INTO catalog_meta(tenant_id,source,source_name,imported_at,record_count,data_date) VALUES($t,$s,$n,$i,$c,$d)";
        c.Parameters.AddWithValue("$t",tenant.ToString());c.Parameters.AddWithValue("$s",source);c.Parameters.AddWithValue("$n",name);c.Parameters.AddWithValue("$i",DateTimeOffset.UtcNow.ToString("O"));
        c.Parameters.AddWithValue("$c",count);c.Parameters.AddWithValue("$d",(object?)date??DBNull.Value);c.ExecuteNonQuery();
    }

    private static List<string> ParseCsvLine(string line)
    {
        var result=new List<string>();var sb=new StringBuilder();var quoted=false;
        for(var i=0;i<line.Length;i++)
        {
            var ch=line[i];
            if(ch=='"'){ if(quoted && i+1<line.Length && line[i+1]=='"'){sb.Append('"');i++;} else quoted=!quoted; }
            else if(ch==';'&&!quoted){result.Add(sb.ToString());sb.Clear();}
            else sb.Append(ch);
        }
        result.Add(sb.ToString());return result;
    }
    private static decimal ParseDecimal(string? s) => decimal.TryParse(s,NumberStyles.Any,De,out var v)?v:decimal.TryParse(s,NumberStyles.Any,CultureInfo.InvariantCulture,out v)?v:0m;
    private static int ParseInt(string? s) => int.TryParse(s,NumberStyles.Any,De,out var v)?v:0;
    private static string? Val(SqliteDataReader r,int i)=>r.IsDBNull(i)?null:r.GetString(i);
    private static int? IntVal(SqliteDataReader r,int i)=>r.IsDBNull(i)?null:r.GetInt32(i);
    private static decimal? DecVal(SqliteDataReader r,int i)=>r.IsDBNull(i)?null:r.GetDecimal(i);
    private static async Task ReadExact(Stream s, byte[] buffer, CancellationToken ct)
    {
        var read=0;while(read<buffer.Length){var n=await s.ReadAsync(buffer.AsMemory(read,buffer.Length-read),ct);if(n==0)throw new EndOfStreamException();read+=n;}
    }
    private sealed record DbfField(string Name, byte Type, int Length);
}
