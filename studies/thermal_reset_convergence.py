"""Reproducible one-cheek OFF-FACE study and local store budget. No human settings."""
from dataclasses import replace
import json
from pathlib import Path
from masck_one.thermal_reset_hardware import cassette,dock,Parameters
from masck_one.thermal_reset_physics import Store,FixtureInputs,transient,dock_reset,dock_transient,architecture_trade,dewpoint_screen


def study():
    p=Parameters();parts,refs,g=cassette(p)
    # Explicit unqualified study properties. Values are not a material selection.
    metal_density_g_mm3=.0027;metal_cp_J_gK=.9;metal_k_W_mK=180.
    PCM_k_W_mK=.2
    metal_mass_g=sum(parts[k].Volume()*metal_density_g_mm3 for k in
                      ('finned_store_and_choked_plate','store_lid','fill_plug'))
    plate_mass_g=p.plate_width_mm*p.plate_height_mm*p.plate_thickness_mm*metal_density_g_mm3
    # Same conservative planning enthalpy method as source-bound historical study.
    enthalpy=(250*.925-30)*.7
    store=Store(g['cavity_mm3'],.77,.875,enthalpy,2.,(metal_mass_g-plate_mass_g)*metal_cp_J_gK,1.)
    choke_R=p.choke_length_mm*.001/(metal_k_W_mK*g['choke_total_section_mm2']*1e-6)
    pcm_R=g['PCM_maximum_half_pitch_mm']*.001/(PCM_k_W_mK*g['fin_area_mm2']*1e-6)
    inputs=FixtureInputs(store=store,plate_heat_capacity_J_K=plate_mass_g*.9,
        wet_water_equivalent_g=.2,water_cp_J_gK=4.18,
        imposed_load_delta_K=8.,load_conductance_W_K=.25,
        plate_center_edge_W_K=metal_k_W_mK*p.plate_thickness_mm*.001*.018/.0055,
        plate_store_W_K=1/(choke_R+pcm_R),plate_ambient_W_K=.006,
        plate_back_W_K=.012,back_ambient_W_K=.04,back_heat_capacity_J_K=1.,
        sensor_heat_capacity_J_K=.01,sensor_plate_W_K=.01,ambient_delta_K=-5.,
        initial_plate_delta_K=8.,initial_store_enthalpy_J=107.136,motor_to_store_W=0.)
    cases={}
    for label,phases in {
        'cool_only':[('COOL',180.,0.)],
        'cool_then_warm':[('COOL',180.,0.),('WARM',60.,3.)],
        'warm_then_cool':[('WARM',60.,3.),('COOL',180.,0.)],
        'repeated_cool_without_reset':[('COOL_1',180.,0.),('COOL_2',180.,0.),('COOL_3',180.,0.)],
    }.items():cases[label]=transient(inputs,phases)
    # Asymmetry is deliberately retained rather than averaged into global reserve.
    asymmetric={side:transient(replace(inputs,load_conductance_W_K=h,
                    initial_store_enthalpy_J=H),[('COOL',180.,0.)])
                for side,h,H in [('LEFT',.40,160.),('RIGHT',.15,54.272)]}
    sensitivity=[]
    for conductance in (.10,.25,.50):
        for wet in (.0,.2,2.):
            result=transient(replace(inputs,load_conductance_W_K=conductance,
                                    wet_water_equivalent_g=wet),[('COOL',180.,0.)])
            sensitivity.append(dict(load_W_K=conductance,water_equivalent_g=wet,
                margin_J=result['phases'][-1]['latent_planning_margin_J'],
                plate_delta_K=result['phases'][-1]['plate_delta_K'],
                load_removed_J=result['load_energy_J']))
    warm_sensitivity=[]
    for power in (2.,3.,4.):
        result=transient(inputs,[('WARM',60.,power)])
        warm_sensitivity.append(dict(heater_W=power,**result))
    reset=[]
    # Half the shared sink area is assigned per cheek. Charging heat is likewise
    # apportioned; no cheek can consume the other cheek's unused reset conductance.
    sink_area=.036;energy=cases['cool_then_warm']['reset_energy_to_solidus_J']
    for delta in (-2.,2.,5.):
        for hcontact in (300.,1000.,3000.):
            for charging in (0.,.25):
                result=dock_reset(energy,delta,g['plate_area_mm2'],hcontact,sink_area/2,5.,.8,
                                  choke_R+pcm_R,charging)
                reset.append(dict(store_above_ambient_K=delta,contact_h_W_m2K=hcontact,
                                  charging_heat_per_cheek_W=charging,**result))
    # Full reset network: same finite sink serves both independently tracked
    # cheeks. Include plate/film/sensor/back energy, not just stored PCM heat.
    dock_parts=dock(p,g['plate_front_z_mm'])
    sink_mass_g=dock_parts['dock_receiver_heat_sink'].Volume()*metal_density_g_mm3
    reset_cases={}
    nominal=cases['warm_then_cool']['reset_initial_state']
    for label,ambient,charging,hleft,hright,initial in [
        ('nominal',-5.,0.,1000.,1000.,{'LEFT':nominal,'RIGHT':nominal}),
        ('charge_during_reset',-5.,.5,1000.,1000.,{'LEFT':nominal,'RIGHT':nominal}),
        ('weak_left_contact',-5.,0.,50.,1000.,{'LEFT':nominal,'RIGHT':nominal}),
        ('warm_room',-2.,0.,1000.,1000.,{'LEFT':nominal,'RIGHT':nominal}),
        ('warm_room_charging',-2.,.5,1000.,1000.,{'LEFT':nominal,'RIGHT':nominal}),
        ('ambient_above_solidus',2.,0.,1000.,1000.,{'LEFT':nominal,'RIGHT':nominal}),
        ('asymmetric_cheeks',-5.,0.,1000.,1000.,{s:r['reset_initial_state'] for s,r in asymmetric.items()}),
    ]:
        result=dock_transient({'LEFT':store,'RIGHT':store},initial,
            contact_W_K={s:h*g['plate_area_mm2']*1e-6 for s,h in [('LEFT',hleft),('RIGHT',hright)]},
            store_plate_W_K={s:inputs.plate_store_W_K for s in initial},
            sink_heat_capacity_J_K=sink_mass_g*metal_cp_J_gK,sink_ambient_W_K=sink_area*5.*.8,
            ambient_delta_K=ambient,plate_back_W_K=inputs.plate_back_W_K,
            back_ambient_W_K=inputs.back_ambient_W_K,plate_ambient_W_K=inputs.plate_ambient_W_K,
            charging_heat_W=charging)
        reset_cases[label]=dict(ambient_delta_K=ambient,charging_W=charging,
            contact_h_W_m2K={'LEFT':hleft,'RIGHT':hright},**result)
    return dict(schema='MASCK_ONE_THERMAL_RESET_CONVERGENCE',physical_validation=False,
        historical_source='2bcdba02e9ee30e86baa74e7cecc9095e8bf4a71',
        historical_reproduced_global_reserves_J={'post_recovery_0p4mL':345.13461698151923,'full_water_4mL':3.1067485045566627},
        selected_bench_architecture='PASSIVE_STORE_THROTTLED_SHARED_PLATE; RESISTIVE_WARM_INPUT; DIRECT_PLATE_DOCK_RESET',
        production_V1_status='NOT_FROZEN; PASSIVE_AMPLITUDE_MODULATION_AND_PACKAGE_REQUIRE_VALIDATION',
        geometry=g,properties_status='UNQUALIFIED_STUDY_INPUTS_NOT_SUPPLIER_SELECTION',
        per_cheek=dict(PCM_mass_g=store.mass_g,metal_mass_g=metal_mass_g,
            planning_capacity_J=store.capacity_J,choke_K_W=choke_R,PCM_internal_screen_K_W=pcm_R,
            plate_store_W_K=inputs.plate_store_W_K,plate_mass_g=plate_mass_g),
        two_cheek_known_mass_DOE_g=2*(store.mass_g+metal_mass_g),
        unknown_mass='INSULATION_HEATER_SENSORS_RETAINER_ENCAPSULATION_HARNESS_AND_MOUNTS',
        original_WARM_reservation_depth_mm=2.4,new_passive_fixture_depth_mm=p.store_depth_mm+p.choke_length_mm+p.plate_thickness_mm,
        shell_growth_required='UNKNOWN_UNTIL_CURRENT_EXTERIOR_AND_FRAME_CHECK',
        cases=cases,asymmetric_cheeks=asymmetric,cooling_sensitivity=sensitivity,warm_sensitivity=warm_sensitivity,
        dock_reset=reset,dock_reset_transient=reset_cases,
        dock_only_mass_DOE_g={'metal_sink':sink_mass_g,'polymer_cradle':'DENSITY_UNSELECTED'},
        trade=architecture_trade(350.,180.,1.,5.),
        condensation=[dict(ambient_C=t,RH_percent=rh,**dewpoint_screen(t,rh,t-3.,1.))
                      for t,rh in [(22.,40.),(25.,60.),(28.,80.),(30.,90.)]],
        faults={'heater_stuck_on':'INDEPENDENT_HARDWARE_CUTOFF_REQUIRED; NOT_IMPLEMENTED_ELECTRONICALLY',
                'sensor_open_short_detached':'INHIBIT_ENERGIZED_TEST; SECOND_INDEPENDENT_SENSOR_WELL',
                'store_unready':'COOL_UNAVAILABLE; NO_READINESS_FROM_PLATEAU_TEMPERATURE_ALONE',
                'dock_contact_absent':'RESET_TIME_MODEL_INVALID; CONTACT_RESPONSE_MUST_BE_OBSERVED',
                'ambient_above_solidus':'PASSIVE_RESET_IMPOSSIBLE; ACTIVE_OFF_FACE_SINK_OR_MODE_UNAVAILABLE'},
        unresolved=['CONTACT_LOAD_AND_PCM_PROPERTIES','REAL_LOCAL_MOTOR_HEAT_COUPLING','CLEANSER_AND_CONDENSATE_ENTHALPY',
                    'WET_DRY_BARRIER_QUALIFICATION','CURRENT_OWNER_WHOLE_PRODUCT_COEXISTENCE','HEATER_AND_FAULT_HARDWARE_SELECTION'])


if __name__=='__main__':
    result=study();out=Path('studies/thermal_reset_convergence_results.json')
    out.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('per_cheek','two_cheek_known_mass_DOE_g','cases','asymmetric_cheeks')},indent=2))
