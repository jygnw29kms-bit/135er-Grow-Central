/* Grow Central Indoor-Zelt-Wiki – eigenständig formulierte Praxisartikel, Quellenlinks,
 * keine automatische Geräteänderung. Alle Pflanzenkulturen, Cannabis als Profil. */
(()=>{
'use strict';
const mount=document.getElementById('cannabisWikiSections');
if(!mount)return;
const sources={
 usask:'https://gardening.usask.ca/gardening-advice/sorted-by-plant/cannabis.php',
 vent:'https://gardening.usask.ca/articles-and-lists/articles-cannabis/articles-indoor-growing/ventilation.php',
 veg:'https://gardening.usask.ca/articles-and-lists/articles-cannabis/articles-growth-cycle/vegetative-growth.php',
 flower:'https://gardening.usask.ca/articles-and-lists/articles-cannabis/articles-growth-cycle/flowering.php',
 seedlings:'https://gardening.usask.ca/articles-and-lists/articles-cannabis/articles-growth-cycle/seedlings.php',
 germ:'https://gardening.usask.ca/articles-and-lists/articles-cannabis/articles-growth-cycle/germination.php',
 water:'https://gardening.usask.ca/articles-and-lists/articles-cannabis/articles-indoor-growing/watering-your-cannabis-plants.php',
 dry:'https://gardening.usask.ca/articles-and-lists/articles-cannabis/drying-cannabis.php',
 light:'https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/lighting-for-indoor-plants',
 hydro:'https://extension.umn.edu/garden-and-home/yard-and-garden/gardening-in-minnesota/small-scale-hydroponics',
 pest:'https://www1.maine.gov/dacf/php/integrated_pest_management/documents/GuidanceforPreventingandManagingPestsinMaineMedicalMarijuana10-15-15.pdf'
};
const A=[
{group:'Planung',title:'Zeltstandort, Abmessungen & Traglast',body:[
'Ein Growzelt ist eine kontrollierte Umgebung innerhalb eines Raumes. Standort trocken, tragfähig, gut zugänglich und mit ausreichend Platz für Abluftschlauch, Türöffnung und Wartung wählen.',
'Die wirksame Pflanzenhöhe ist geringer als die Zelthöhe: Topf, Leuchte, Aufhängung und Sicherheitsabstände abziehen. Vor Installation die zulässige Last der Zeltstangen und Lampenaufhängung prüfen.',
'Kalte Betonböden vom Topfboden thermisch trennen; Wände und Dach auf Feuchte und Kondensation kontrollieren. Ein Zelt ersetzt keine sichere Gebäudeisolierung.'
],tips:['Vor der ersten Pflanze Aufbau, Stromaufnahme, Luftwege und Sensoren 24 Stunden ohne Pflanzen testen.','Zugänglichkeit aller Töpfe und Abluftfilter vorab prüfen.'],sources:['usask','vent']},
{group:'Planung',title:'Elektrik, Wasser & Brandschutz',body:[
'Nur technisch einwandfreie, für Feuchte und Last geeignete Geräte und Leitungen verwenden. Steckverbindungen und Netzteile außerhalb möglicher Spritzwasserbereiche anordnen; Kabel mit Tropfschleifen verlegen.',
'Last von LED, Abluft, Umluft und Heizung zusammenrechnen und die Stromkreisbelastbarkeit prüfen. FI/RCD-Schutz und ordnungsgemäße Schutzleiter verwenden; keine überlasteten Mehrfachsteckdosen oder hintereinander gesteckten Leisten.',
'Heizgeräte niemals direkt an Textilien, Zeltwand oder Kunststoffbehälter stellen; Herstellerabstände einhalten. Wasserbehälter standsicher aufstellen, Tropfschalen regelmäßig leeren.'
],tips:['Schaltgeräte und WLAN-Steckdosen müssen für den jeweiligen Verbraucher einschließlich Einschaltstrom ausgelegt sein.','Vor Reinigung und Arbeiten an Elektrik spannungsfrei schalten.'],sources:['usask']},
{group:'Klima',title:'Zuluft, Abluft, Unterdruck & Aktivkohle',body:[
'Frische Luft tritt über geeignete Zuluftöffnungen ein; Abluft führt Wärme, Wasserdampf und Gerüche ab. Aktivkohlefilter bei Bedarf vor den Abluftventilator montieren. Luftführung kurz und knickarm halten.',
'Die theoretische Luftwechselrate ergibt sich aus Fördervolumenstrom geteilt durch Zeltvolumen. Datenblattwerte gelten ohne zusätzliche Verluste: Filter, Schlauchbögen und Unterdruck senken die tatsächlich transportierte Menge.',
'Moderater Unterdruck hilft gegen unkontrollierten Geruchsaustritt. Stark eingesogene Zeltwände sind kein Gütesiegel, sondern ein Hinweis auf zu wenig Zuluft.'
],tips:['Bei hoher Feuchte zuerst Luftwechsel und Raumluft prüfen, dann erst einen weiteren Entfeuchter erwägen.','Vorfilter regelmäßig reinigen; verschmutzter Filter reduziert den Luftstrom.'],sources:['vent']},
{group:'Klima',title:'Umluft, Totzonen und Sanftanlauf',body:[
'Umluft bewegt die Luft zwischen und unter Blättern, ohne sie automatisch aus dem Raum abzuführen. Abluft und Umluft erfüllen unterschiedliche Aufgaben.',
'Blätter sollten leicht bewegt werden, nicht dauerhaft stark verbogen. Direkten, konstanten Luftstrahl auf empfindliche Sämlinge vermeiden.',
'Bei Lüftern mit Sanftanlauf folgt der Ist-RPM-Wert dem Sollwert zeitversetzt. Während der Anlaufphase mehrere echte Messungen erfassen, bevor eine Anlaufstörung bewertet wird.'
],tips:['Messpunkte auf Kronenhöhe und in Bodennähe vergleichen.','Wenn der Lüfter aus ist, zeigt Grow Central „Aus“ statt „0 RPM“.'],sources:['vent']},
{group:'Klima',title:'Temperatur, Luftfeuchte & VPD',body:[
'Temperatur und relative Luftfeuchte gemeinsam betrachten: dieselbe relative Feuchte bedeutet bei unterschiedlichen Temperaturen nicht dieselbe Wasserdampfmenge.',
'VPD beschreibt die Differenz zwischen Sättigungsdampfdruck und tatsächlichem Dampfdruck. Für eine genaue Blatt-VPD-Betrachtung ist auch die Blatttemperatur nötig; eine Luft-VPD-Schätzung darf nicht als Blattmessung ausgegeben werden.',
'Richtwerte sind kultur-, sorten-, entwicklungsphasen- und tageszeitabhängig. Grow Central soll Grün/Gelb/Rot nur dann zeigen, wenn die Kulturphase tatsächlich bekannt ist oder ausdrücklich ausgewählt wurde.'
],tips:['Fühler nicht unmittelbar unter eine heiße Leuchte oder in die Ausblasströmung hängen.','Licht- und Dunkelphasen getrennt auswerten, besonders bei feuchten Nächten.'],sources:['veg','flower','vent']},
{group:'Licht',title:'LED, PPFD, DLI & Photoperiode',body:[
'PPFD misst die am Blatt eintreffende Anzahl photosynthetisch nutzbarer Lichtquanten pro Fläche und Sekunde. Lampenleistung in Watt oder eine Dimmstufe in Prozent ersetzt keine PPFD-Messung.',
'Die Tageslichtsumme DLI ergibt sich aus PPFD × Beleuchtungsstunden × 0,0036 (mol/m²/Tag). Beispiel: 400 µmol/m²/s bei 16 Stunden entsprechen 23,04 mol/m²/Tag.',
'Die Lampe möglichst gleichmäßig über der Pflanzenfläche aufhängen. Mehrere Messpunkte an Ecken und Mitte decken Hotspots und Schatten auf. Lampenabstände und Leistung nach Herstellerangaben und gemessener Beleuchtung wählen.'
],tips:['Neue Beleuchtung schrittweise anpassen und sichtbare Blattreaktionen protokollieren.','Lichttimer auf Stromausfall und Zeitzonenwechsel prüfen.'],sources:['light','usask']},
{group:'Licht',title:'Photoperiodische Pflanzen und Automatics',body:[
'Cannabis mit photoperiodischer Blütenreaktion braucht für den Blühimpuls lange, ununterbrochene Nächte. Ein verbreitetes Innenschema ist 18/6 in der Wachstums- und 12/12 in der Blütephase.',
'Autoflowering-Typen sind weitgehend taglängenunabhängig. Unterschiedliche Sorten und Kulturen können daher im gemeinsamen Zelt unterschiedliche Lichtwünsche haben.',
'Ungeplante Lichtquellen während der Dunkelphase vermeiden. Die gewählte Photoperiode als Teil des Kulturprofils dokumentieren; nicht jedem Nutzer automatisch 12/12 aufzwingen.'
],tips:['Automatics und Photoperiodische gemeinsam nur mit bewusstem Kompromiss beim Tageslichtplan kultivieren.','Bei Problemen zuerst die tatsächlichen Schaltzeiten im Verlauf prüfen.'],sources:['usask','veg','flower']},
{group:'Wasser',title:'Gießen in Erde und Kokos',body:[
'Wasser langsam und gleichmäßig zuführen. Sehr trockene Substrate können Wasserkanäle bilden: Feuchtigkeit verteilt sich dann ungleichmäßig.',
'Bewässerungsbedarf ergibt sich aus Topfgewicht, Wurzelentwicklung, Substrat, Temperatur und Lichtmenge; keine pauschalen Milliliter pro Pflanze verwenden.',
'Drainage und Sauerstoff im Wurzelraum sind wichtig. Staunässe vermeiden und Untersetzer kontrollieren. In Kokos unterscheiden sich Nährstoff- und Bewässerungsmanagement deutlich von vorgedüngter Erde.'
],tips:['Vor und nach dem Gießen Topfgewicht und Bodenfeuchte notieren.','Bodensensoren auf das konkrete Substrat kalibrieren, sonst sind Prozentwerte wenig aussagekräftig.'],sources:['water','usask']},
{group:'Wasser',title:'pH, EC und Wasserqualität',body:[
'pH beeinflusst die Verfügbarkeit einzelner Nährstoffe. Die passenden Bereiche hängen von Kultur und Substrat ab; Erdsubstrate und Hydroponik sind nicht identisch.',
'EC beschreibt die elektrische Leitfähigkeit als indirekten Hinweis auf gelöste Salze, nicht die Konzentration eines einzelnen Nährstoffes. Temperaturkompensation und Kalibrierung des Messgeräts beachten.',
'Leitungswasser kann stark unterschiedliche Härte, Alkalinität und Salzgehalte haben. Änderungen nicht allein aus einem Einzelwert ableiten.'
],tips:['Messgeräte mit geeigneten Referenzlösungen kalibrieren und den Zeitpunkt im Growbuch erfassen.','Gießwasser und Drainage als getrennte Messungen dokumentieren.'],sources:['water','hydro']},
{group:'Wasser',title:'Düngung und Mangelerscheinungen',body:[
'Pflanzen benötigen neben Kohlenstoff, Wasser und Licht Makro- und Spurennährstoffe. Die optimale Versorgung hängt von Substratvorrat, Wasserqualität, Wachstum und Kultur ab.',
'Gelbe Blätter, Flecken oder verbrannte Spitzen sind keine eindeutige Diagnose: falsche Bewässerung, pH, Wurzelstress, Salzbelastung, Licht und Schädlinge können ähnliche Bilder erzeugen.',
'Düngergaben nur auf überprüfbare Ursachen hin ändern. Ein vollständiges Protokoll enthält Produkt, Menge, Datum, Wasserwert und beobachtete Wirkung.'
],tips:['Nicht mehrere Dünger oder Korrekturmittel gleichzeitig ändern, sonst lässt sich die Wirkung nicht zuordnen.','Vor einer Mangeldiagnose zuerst Wurzelraum, Wasser und pH plausibilisieren.'],sources:['usask','water']},
{group:'Kultur',title:'Keimung, Sämlinge & Umtopfen',body:[
'Saatgut sauber und vorsichtig handhaben; die Keimumgebung gleichmäßig feucht, aber nicht nass halten. Jungpflanzen reagieren empfindlich auf starke Nährstoffkonzentrationen und große Klimaschwankungen.',
'Beim Umtopfen den Wurzelballen schützen, geeignetes Substrat verwenden und danach die Erholung beobachten.',
'Pflanzen-ID, Herkunft, Startdatum und Entwicklungsphase direkt beim Einsetzen in den Grow Central-Pflanzenstamm aufnehmen.'
],tips:['Fotos vom Sämling zur späteren Vergleichsdokumentation machen.','Kleine Pflanzen nicht ausschließlich nach dem Feuchtewert eines einzigen Sensors bewässern.'],sources:['germ','seedlings']},
{group:'Kultur',title:'Wachstumsphase, Formgebung und Platzbedarf',body:[
'Mit zunehmender Blattfläche steigen in der Regel Bedarf an Licht, Wasser und Luftbewegung. Pflanzen dürfen weder Leuchten berühren noch Lüfter und Luftwege blockieren.',
'Bindungen, Stützen und Schnittmaßnahmen stressarm durchführen. Jede Kultur reagiert unterschiedlich; Eingriffe nach Bedarf und Gesundheitszustand statt nach starren Kalendertagen planen.',
'Canopy-Höhe und Topfposition dokumentieren: So lassen sich Unterschiede in der Beleuchtung zwischen Pflanzen später nachvollziehen.'
],tips:['Vor Trainingsmaßnahmen ein Foto und einen Journal-Eintrag anlegen.','Tage zwischen Änderungen lassen, damit Reaktionen erkennbar werden.'],sources:['veg']},
{group:'Kultur',title:'Blüte, Reife, Ernte und Hygiene',body:[
'Während dichter Blütenbildung können feuchte, schlecht durchlüftete Stellen ein erhöhtes Risiko für Grauschimmel verursachen. Pflanzen regelmäßig und vorsichtig kontrollieren.',
'Erntezeitpunkte anhand kulturspezifischer Reifemerkmale dokumentieren. Vor Ernte und Verarbeitung saubere, geeignete Werkzeuge und Arbeitsflächen vorbereiten.',
'Bei sichtbarem Schimmel befallenes Material getrennt halten und nicht als unbedenklich behandeln.'
],tips:['Für späte Blüte besonders nächtliche Feuchtespitzen im Verlauf ansehen.','Pro Ernte Charge, Datum, Pflanzen-ID und Umweltbedingungen speichern.'],sources:['flower','pest']},
{group:'Kultur',title:'Trocknen und Lagern',body:[
'Trocknung ist ein eigener Prozess mit Messwerten und Hygieneanforderungen. Ein trockenes, sauberes Zelt mit kontrollierter Zu- und Abluft kann als Trockenraum dienen.',
'Für Cannabis nennt die University of Saskatchewan als Orientierung 16–23 °C und 50–60 % Luftfeuchte während der Trocknung. Keine direkte starke Luftströmung auf die Ware richten.',
'Im Lager auf Verderb, Kondensation und mikrobiologische Risiken achten. Trocknungsparameter nicht ungeprüft auf frische Pflanzen anwenden.'
],tips:['Trocknungsraum vor dem Einbringen reinigen und leere Regelung testen.','Feuchtetrends über Stunden sind aussagekräftiger als ein einzelner Messpunkt.'],sources:['dry']},
{group:'Schutz',title:'Schädlinge erkennen & integrierter Pflanzenschutz',body:[
'Blattunterseiten, junge Triebe und Substratoberflächen regelmäßig auf Insekten, Milben, Larven und Fraßbilder prüfen.',
'Neue Pflanzen möglichst getrennt beobachten. Saubere Werkzeuge, kontrollierte Zuluft und trockene, leicht reinigbare Oberflächen verhindern viele Probleme.',
'Behandlungsmaßnahmen nach Kultur und Zulassung auswählen; keine nicht zugelassenen Pflanzenschutzmittel verwenden.'
],tips:['Gelbtafeln eignen sich zur Beobachtung fliegender Schädlinge, ersetzen aber keine Diagnose.','Befall inklusive Fotos und Fundort festhalten.'],sources:['pest']},
{group:'Schutz',title:'Schimmel, Kondenswasser und muffiger Geruch',body:[
'Kondenswasser an Zeltwand, Dach oder Abluftleitung deutet auf ein ungünstiges Feuchte-Temperatur-Gefälle hin. Auch kalte Gebäudeflächen beachten.',
'Grauschimmel kann im dichten Pflanzenbestand entstehen. Umgebungsfeuchte reduzieren, Luftwege prüfen und befallene Teile sachgerecht entfernen; kontaminierte Teile nicht konsumieren.',
'Starker Geruch ist kein alleiniger Beleg für Schimmel. Sichtkontrolle, Klimahistorie und bei Bedarf fachliche Untersuchung sind aussagekräftiger.'
],tips:['Alarm auf über längere Zeit erhöhte relative Luftfeuchte vorsehen statt nur auf Momentanwerte.','Abluft möglichst nicht in einen kalten, schlecht belüfteten Zwischenraum führen.'],sources:['flower','vent','pest']},
{group:'Grow Central',title:'Sensoren, Kalibrierung & Echtzeitdaten',body:[
'Temperatur und Feuchte auf Pflanzenhöhe messen. Bei größeren Zelten mehrere Positionen verwenden; einzelne Werte können lokale Hotspots verdecken.',
'Bodenfeuchtesensoren brauchen eine Kalibrierung im verwendeten Medium. Zwischen Ist-Messwert, Hersteller-Schätzwert und Sollwert unterscheiden.',
'PPFD, CO₂ und Blatt-VPD nur als gemessen kennzeichnen, wenn entsprechende Sensorik tatsächlich vorhanden ist. Lüfter-CFM und statischer Druck aus einer Herstellerformel sind keine Messungen.'
],tips:['Bei Grow Central Rohwert, Einheit, Messquelle, Zeitstempel und Alter jedes Datenpunkts protokollieren.','Echte RPM-Verläufe inklusive Sanftanlauf speichern.'],sources:['light','vent']},
{group:'Grow Central',title:'Profile, Alarme & Grow-Vergleich',body:[
'Kulturprofile enthalten Kultur, Sorte, Phase, Startdatum, angestrebte Klimabereiche, Lichtprogramm, Substrat und Pflegeereignisse.',
'Warnungen sollen nach Dauer, Messgüte und tatsächlicher Phase gewichtet werden. Eine kurze Feuchtespitze beim Gießen ist nicht automatisch ein Anlagenfehler.',
'Vergleiche zwischen Durchläufen sollten Pflanzen-ID, Kulturphase und Datum synchronisieren, nicht nur unterschiedliche Kalendermonate.'
],tips:['Je Kulturphase Vorher-Nachher-Screenshots und Messstatistiken archivieren.','Immer zwischen Sollwert, Istwert und geschätztem Wert unterscheiden.'],sources:['usask','light']},
{group:'Fehlerhilfe',title:'Symptom: Gelbe Blätter oder stockendes Wachstum',body:[
'Prüfreihenfolge: Wurzelzone und Gießrhythmus, Lichtdistanz und echte PPFD, Temperatur und Feuchte, anschließend pH/EC und Schädlinge.',
'Blattalter und Muster notieren: zuerst ältere oder jüngere Blätter, punktförmig oder flächig, mehrere Pflanzen betroffen oder nur eine?',
'Nicht aufgrund eines Fotos automatisch einen spezifischen Nährstoffmangel diagnostizieren.'
],tips:['Nur eine Ursache nach der anderen verändern und zeitlich dokumentieren.','Daten der letzten 48–72 Stunden vor Auftreten des Symptoms vergleichen.'],sources:['water','pest']},
{group:'Fehlerhilfe',title:'Symptom: Zu warm, zu feucht, trockene Spitzen',body:[
'Bei Hitze: reale Raumzulufttemperatur, Lampenleistung, Abluftweg und Filter prüfen. Mehr Abluft hilft nur, wenn zugeführte Luft ausreichend kühl ist.',
'Bei hoher Feuchte: Wasserquellen, Dunkelphase, Luftaustausch, dichten Bestand und die Raumluft außerhalb des Zelts prüfen.',
'Trockene Blattspitzen können durch mehrere Stressfaktoren entstehen; nicht blind zusätzliche Wassergaben oder Dünger auslösen.'
],tips:['Zeltwerte mit Werten außerhalb des Zelts vergleichen.','Klima vor und nach dem Einschalten der Beleuchtung getrennt prüfen.'],sources:['vent','flower']},
{group:'Fehlerhilfe',title:'Symptom: Lüfter 0 RPM trotz Sollwert',body:[
'Zuerst den Gerätestatus prüfen: ausgeschaltet bedeutet ausdrücklich „Aus“. Nach dem Einschalten können Softstart und Verzögerung der Telemetrie vorliegen.',
'Erst wenn über mehrere Messzyklen nach angemessener Anlaufphase weiterhin keine echte Drehzahl erkannt wird, Verbindung, Lüfter und Sensor prüfen.',
'CFM oder Pa aus Prozentwerten bleiben klar als Schätzung markiert. Es darf kein Messwert vorgetäuscht werden.'
],tips:['Sollwertwechsel mit Zeitstempel protokollieren und Rampendauer über reale Messungen ableiten.','Bei unverändertem RPM nicht automatisch wiederholt Motorbefehle senden.'],sources:['vent']},
{group:'Praxis',title:'Checkliste: vor dem ersten Grow',body:[
'Zelt standsicher und vollständig; Abluftführung und Filter montiert; Stromversorgung geschützt; Wasser sicher von Elektrik getrennt.',
'Beleuchtung, Luftwechsel, Temperatur-/Feuchtefühler und Geräteidentitäten getestet; Zeitschaltpläne auf tatsächlichen Wechsel kontrolliert.',
'Pflanze/Kultur im Growbuch angelegt, Sensoren kalibriert, Baseline von Zelt leer beziehungsweise ohne Pflanzen gespeichert.'
],tips:['Leerlaufprüfung über mehrere Licht-/Dunkelzyklen durchführen.','Anlagenschutz und Warnmeldungen erst prüfen, bevor empfindliche Jungpflanzen eingesetzt werden.'],sources:['usask','vent']},
{group:'Praxis',title:'Checkliste: täglich und wöchentlich',body:[
'Täglich: Pflanzen sichtbar kontrollieren, Klima-Min/Max und Sensoralter prüfen, Gießbedarf nach Substrat beurteilen, auffällige Blätter fotografieren.',
'Wöchentlich: Lüfter, Filtervorstufe, Auffangschalen, Schläuche, Wasserwerte und Lampenaufhängung inspizieren; Trends und Alarme durchsehen.',
'Nach jedem Eingriff: Was wurde verändert, wann, an welcher Pflanze, mit welchem Sollwert und mit welcher beobachteten Wirkung?'
],tips:['Abweichungen zuerst dokumentieren, dann gezielt beheben.','Nicht ausgeführte oder unbestätigte Gerätebefehle getrennt von Erfolgen archivieren.'],sources:['pest','usask']}
];
const t=(tag,text,cls)=>{const e=document.createElement(tag);if(text!=null)e.textContent=text;if(cls)e.className=cls;return e};
mount.replaceChildren();
const toolbar=t('div',null,'gc-wiki-toolbar'),search=t('input'),group=t('select'),counter=t('span','', 'gc-wiki-count');
search.type='search';search.placeholder='Zelt-Wiki durchsuchen: Klima, LED, Gießen, Schimmel …';search.setAttribute('aria-label','Zelt-Wiki durchsuchen');
const groups=[...new Set(A.map(x=>x.group))];group.append(t('option','Alle Themen'));group.firstChild.value='';
for(const value of groups){const option=t('option',value);option.value=value;group.append(option)}
toolbar.append(search,group,counter);
const list=t('div',null,'gc-wiki-articles');mount.append(toolbar,list);
function render(){
 const q=search.value.trim().toLocaleLowerCase('de'),g=group.value;
 list.replaceChildren();let matched=0;
 for(const entry of A){
  if(g&&entry.group!==g)continue;
  const blob=[entry.group,entry.title,...entry.body,...entry.tips].join(' ').toLocaleLowerCase('de');
  if(q&&!blob.includes(q))continue;
  matched++;
  const details=t('details',null,'gc-wiki-article');
  const summary=t('summary');summary.append(t('small',entry.group),t('strong',entry.title));details.append(summary);
  const content=t('div',null,'gc-wiki-content');
  for(const paragraph of entry.body)content.append(t('p',paragraph));
  const heading=t('h5','Praxis-Tipps');content.append(heading);
  const ul=t('ul');for(const tip of entry.tips)ul.append(t('li',tip));content.append(ul);
  const foot=t('p',null,'gc-wiki-references');foot.append(t('strong','Quellen: '));
  for(const key of entry.sources){const link=t('a',key.toUpperCase());link.href=sources[key];link.target='_blank';link.rel='noopener noreferrer';foot.append(link,t('span',' · '))}
  content.append(foot);details.append(content);list.append(details);
 }
 counter.textContent=matched+' / '+A.length+' Artikel';
 if(!matched)list.append(t('p','Keine passenden Wiki-Artikel gefunden.'));
}
search.addEventListener('input',render);group.addEventListener('change',render);render();
})();