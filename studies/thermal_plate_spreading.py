from masck_one.thermal_reset_physics import plate_field
import json
from pathlib import Path

def study():
    rows=[]
    for posts in (((-8.,0.),(8.,0.)),((-8.,-8.),(-8.,8.),(8.,-8.),(8.,8.))):
        for t in (.6,1.):
            for heater in ((12.,18.),(18.,24.)):
                r=plate_field(width_mm=22.,height_mm=28.,thickness_mm=t,conductivity_W_mK=180.,
                    heater_W=3.,heater_width_mm=heater[0],heater_height_mm=heater[1],
                    post_xy_mm=posts,total_store_W_K=.2237332234945218,store_delta_K=.5,
                    load_W_K=.25,load_delta_K=8.,ambient_W_K=.018,ambient_delta_K=-5.,
                    post_width_mm=1.3 if len(posts)==2 else .92)
                r.pop('temperature_delta_grid_K')
                rows.append(dict(posts=posts,thickness_mm=t,heater_size_mm=heater,**r))
    selected=[]
    for n in (1,2):
        r=plate_field(width_mm=22.,height_mm=28.,thickness_mm=1.,conductivity_W_mK=180.,
            heater_W=3.,heater_width_mm=18.,heater_height_mm=24.,
            post_xy_mm=((-8.,-8.),(-8.,8.),(8.,-8.),(8.,8.)),total_store_W_K=.2237332234945218,
            store_delta_K=.5,load_W_K=.25,load_delta_K=8.,ambient_W_K=.018,ambient_delta_K=-5.,
            post_heater_fraction=.6,nx=22*n,ny=28*n)
        r.pop('temperature_delta_grid_K');selected.append(r)
    return dict(input_status='ASSUMED_METAL_PROPERTIES_AND_INERT_LOAD',cases=rows,
                selected_distributed_heater=selected,physical_validation=False)

if __name__=='__main__':
    r=study();Path('studies/thermal_plate_spreading_results.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps(r,indent=2))
