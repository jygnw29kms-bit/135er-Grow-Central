"""Compare two Grow Central plants by age using permanent room history.

The common room climate applies to all plants in that room at a given time.
A comparison is correlation, not proof of cause and not a claim of per-plant
temperature sensing. Empty historical weeks remain missing, not zero.
"""
from __future__ import annotations

from collections import defaultdict
from contextlib import closing
from datetime import date,datetime,timedelta,timezone
from fastapi import APIRouter,Depends,HTTPException,Query
from app.security import require_write_auth
from app import history_archive
from app.rooms import load_state

router=APIRouter(prefix="/api/v1/history",tags=["grow comparison"],
                 dependencies=[Depends(require_write_auth)])

TRACKED=("temperature_c","humidity_percent","soil_moisture_percent",
         "soil_temperature_c","vpd_kpa","co2_ppm","ppfd_umol_m2_s",
         "ec_ms_cm","ph","power_w","fan_rpm","fan_setpoint_percent",
         "lamp_brightness_percent","airflow_cfm","pressure_pa")

def plant_info(plant_id: str):
    state=load_state()
    plant=next((p for p in state.get("plants",[]) if p.get("id")==plant_id),None)
    if not plant:raise HTTPException(404,"Pflanze nicht gefunden")
    raw=plant.get("start_date") or plant.get("created_at") or ""
    try:start=date.fromisoformat(str(raw)[:10])
    except ValueError:raise HTTPException(422,"Pflanze hat kein gültiges Startdatum")
    return {"id":plant_id,"name":plant.get("name",""),"room_id":plant["room_id"],
            "start_date":start.isoformat(),"start":start,"phase":plant.get("phase")}

def weekly_series(plant: dict, weeks: int) -> dict:
    start=plant["start"];end=start+timedelta(weeks=weeks)
    today=datetime.now(timezone.utc).date()
    sums=defaultdict(lambda: [0,0.0,float("inf"),float("-inf")])
    count=0
    with closing(history_archive.connect()) as db:
        items=db.execute("""SELECT recorded_at,metric,value,source_kind
             FROM points WHERE room_id=? AND substr(recorded_at,1,10)>=?
             AND substr(recorded_at,1,10)<? ORDER BY recorded_at""",
            (plant["room_id"],start.isoformat(),end.isoformat()))
        for row in items:
            if row["metric"] not in TRACKED:continue
            try:day=date.fromisoformat(row["recorded_at"][:10])
            except ValueError:continue
            week=(day-start).days//7
            if not 0<=week<weeks:continue
            item=sums[week,row["metric"]]
            item[0]+=1;item[1]+=row["value"]
            item[2]=min(item[2],row["value"]);item[3]=max(item[3],row["value"])
            count+=1
    output=[]
    for i in range(weeks):
        first=start+timedelta(weeks=i)
        values={}
        for metric in TRACKED:
            if (i,metric) not in sums:continue
            n,total,minimum,maximum=sums[i,metric]
            values[metric]={"mean":round(total/n,3),"min":round(minimum,3),
                            "max":round(maximum,3),"samples":n,
                            "unit":history_archive.UNITS[metric][0],
                            "source_kind":history_archive.UNITS[metric][1]}
        output.append({"week":i+1,"start":first.isoformat(),"has_data":bool(values),
                       "future_week":first>today,"metrics":values})
    return {"samples":count,"weeks":output}

@router.get("/compare-plants")
def compare_plants(plant_a: str=Query(min_length=1,max_length=128),
                   plant_b: str=Query(min_length=1,max_length=128),
                   weeks: int=Query(default=16,ge=1,le=104)):
    a=plant_info(plant_a);b=plant_info(plant_b)
    sa=weekly_series(a,weeks);sb=weekly_series(b,weeks)
    differences=[]
    for i in range(weeks):
        ma=sa["weeks"][i]["metrics"];mb=sb["weeks"][i]["metrics"]
        diffs={metric:{"a":ma[metric]["mean"],"b":mb[metric]["mean"],
                       "delta_b_minus_a":round(mb[metric]["mean"]-ma[metric]["mean"],3),
                       "unit":ma[metric]["unit"],"source_kind":ma[metric]["source_kind"]}
               for metric in ma.keys()&mb.keys()}
        differences.append({"week":i+1,"metrics":diffs})
    def public(plant):return {k:v for k,v in plant.items() if k!="start"}
    return {"alignment":"weeks_since_plant_start","weeks_requested":weeks,
            "a":{"plant":public(a),**sa},"b":{"plant":public(b),**sb},
            "differences":differences,
            "note":"Room readings are shared environment measurements, not individual plant sensors. Missing weeks are never assumed to be zero. Correlation is not causation."}
