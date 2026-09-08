from __future__ import annotations

"""Source-bound Cell 12 battery, dry-bay, PCB and charging package.

Digital CAD packaging evidence only. Cell 12 owns the internal dry-side package and
its closure/seal interface. The visible exterior rear cover is owned by Cell 2 and is
not duplicated here as material. No supplier, ingress, electrical-safety, runtime,
thermal, service-life or physical-performance claim is created by this module.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .authority import Authority, load_authority
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_CELL12_COMPACT_DRY_SIDE_PACKAGE_V2"
SOURCE_MAIN_SHA = "ff76a17fa25276a401fbe57ad02564b771fa1865"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
LOCAL_FRAME_ID = "MASCK_ONE_DRY_BAY_LOCAL_MM"
LEGACY_DONOR_PR = 64
LEGACY_DONOR_HEAD_SHA = "49a32d0c61bd1057ee707ee2ef20b8ff4e6ede01"
LEGACY_DONOR_BLOB_SHA = "59e69a781e4ffcbb581a9f2835c9cb581b3939f2"
EVIDENCE_STATUS = "DIGITAL_DRY_SIDE_PACKAGING_ONLY_NOT_PHYSICAL_OR_ELECTRICAL_VALIDATION"

SOURCE_GIT_BLOB_IDENTITIES = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
)

BATTERY_FAULT_CLEARANCE_XY_MM = 1.5
BATTERY_FAULT_CLEARANCE_Z_MM = 2.0
DRY_BAY_OUTER_MM = (48.0, 66.0, 22.0)
DRY_BAY_CENTER_MM = (0.0, 0.0, -36.0)
DRY_BAY_WALL_MM = 1.8
BATTERY_GUIDE_WALL_MM = 1.5
SUPPORT_RIB_THICKNESS_MM = 1.0
BATTERY_CENTER_MM = (0.0, -2.0, -39.0)
PCB_REFERENCE_MM = (38.0, 22.0, 1.6)
PCB_CENTER_MM = (0.0, 19.0, -29.4)
PCB_SUPPORT_MM = (40.0, 24.0, 1.2)
PCB_SUPPORT_CENTER_MM = (0.0, 19.0, -30.9)
POWER_ZONE_MM = (12.0, 8.0, 1.0)
POWER_ZONE_CENTER_MM = (-10.0, 19.0, -28.4)
CHARGE_RESERVATION_MM = (10.0, 8.0, 4.0)
CHARGE_CENTER_MM = (-23.0, -26.0, -28.5)
CLOSURE_INTERFACE_MM = (46.0, 64.0, 0.4)
CLOSURE_INTERFACE_CENTER_MM = (0.0, 0.0, -47.2)
CLOSURE_INTERFACE_CORNER_RADIUS_MM = 8.0
BATTERY_SERVICE_END_Z_MM = -70.0
LOAD_IDS = ("ACTUATORS_X4", "FRESH_WATER_PUMP", "CLEANSER_PUMP", "WASTE_PUMP", "CONTROL_ELECTRONICS", "HMI_AND_THERMAL_AUXILIARIES")
_REPO_ROOT = Path(__file__).resolve().parents[2]

class DrySidePackageError(ValueError): pass

def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip(): raise DrySidePackageError(f"{label} must be exact nonblank text")
    return value

def _finite(value: object, label: str, *, positive: bool = False) -> float:
    if type(value) not in (int, float): raise DrySidePackageError(f"{label} must be an exact numeric scalar")
    result=float(value)
    if not math.isfinite(result): raise DrySidePackageError(f"{label} must be finite")
    if positive and result <= 0.0: raise DrySidePackageError(f"{label} must be positive")
    return 0.0 if result == 0.0 else result

def _point(value: object, label: str) -> tuple[float,float,float]:
    if type(value) is not tuple or len(value)!=3: raise DrySidePackageError(f"{label} must be an exact XYZ tuple")
    return tuple(_finite(item,f"{label}[{index}]") for index,item in enumerate(value))  # type: ignore[return-value]

def _box(size, center):
    sx,sy,sz=tuple(_finite(item,"box dimension",positive=True) for item in size); cx,cy,cz=_point(center,"box center")
    return cq.Workplane("XY").box(sx,sy,sz,centered=(True,True,True)).translate((cx,cy,cz))

def _rounded_box_xy(size,center,radius_mm): return _box(size,center).edges("|Z").fillet(_finite(radius_mm,"corner radius",positive=True))

def _geometry(solid):
    shape=solid.val()
    if not shape.isValid() or len(shape.Solids())!=1 or float(shape.Volume())<=0.0: raise DrySidePackageError("dry-side geometry must be one valid positive-volume solid")
    bb=shape.BoundingBox(); return {"min_mm":[float(bb.xmin),float(bb.ymin),float(bb.zmin)],"max_mm":[float(bb.xmax),float(bb.ymax),float(bb.zmax)],"spans_mm":[float(bb.xlen),float(bb.ylen),float(bb.zlen)],"volume_mm3":float(shape.Volume())}

def _intersection(first,second):
    value=float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value<0: raise DrySidePackageError("intersection volume must be finite and non-negative")
    return 0.0 if value<1e-8 else value

def _distance(first,second):
    value=float(first.val().distance(second.val()))
    if not math.isfinite(value) or value<0: raise DrySidePackageError("B-rep distance must be finite and non-negative")
    return 0.0 if value<1e-8 else value

def _git_blob_sha(path):
    data=path.read_bytes(); return sha1(f"blob {len(data)}\0".encode("ascii")+data).hexdigest()

def _require_sources():
    for relative_path,expected in SOURCE_GIT_BLOB_IDENTITIES:
        path=_REPO_ROOT/relative_path
        if not path.is_file(): raise DrySidePackageError(f"dry-side source file missing: {relative_path}")
        actual=_git_blob_sha(path)
        if actual!=expected: raise DrySidePackageError(f"dry-side source moved at {relative_path}; expected {expected}, got {actual}")

def _require_authority(authority):
    if type(authority) is not Authority: raise DrySidePackageError("dry-side package requires exact Authority type")
    canonical=load_authority()
    if authority.data!=canonical.data: raise DrySidePackageError("supplied authority differs from released machine authority")
    if str(authority.get("project","authority_revision"))!=AUTHORITY_REVISION: raise DrySidePackageError("dry-side authority revision moved")
    expected=("wearer_right","superior","anterior"); actual=(authority.get("coordinate_system","x_positive"),authority.get("coordinate_system","y_positive"),authority.get("coordinate_system","z_positive"))
    if tuple(authority.get("coordinate_system","origin"))!=(0.0,0.0,0.0) or actual!=expected: raise DrySidePackageError("dry-side package requires canonical world origin and axis signs")

@dataclass(frozen=True,slots=True)
class PackageGeometry:
    geometry_id:str; role:str; solid:cq.Workplane; material_class:str; hygiene_class:str; geometry_status:str
    def __post_init__(self):
        for label,value in (("geometry_id",self.geometry_id),("role",self.role),("material_class",self.material_class),("hygiene_class",self.hygiene_class),("geometry_status",self.geometry_status)): _text(value,label)
        if self.material_class not in {"PHYSICAL_MATERIAL_CANDIDATE","REFERENCE_ONLY","SERVICE_SWEEP_REFERENCE","SEAL_INTERFACE_RESERVATION"}: raise DrySidePackageError("uncontrolled dry-side material class")
        _geometry(self.solid)
    def manifest(self): return {"geometry_id":self.geometry_id,"role":self.role,"material_class":self.material_class,"hygiene_class":self.hygiene_class,"geometry_status":self.geometry_status,"geometry":_geometry(self.solid)}

@dataclass(frozen=True,slots=True)
class CollisionCheck:
    check_id:str; first_id:str; second_id:str; intersection_volume_mm3:float; minimum_distance_mm:float
    def __post_init__(self):
        for label,value in (("check_id",self.check_id),("first_id",self.first_id),("second_id",self.second_id)): _text(value,label)
        _finite(self.intersection_volume_mm3,"intersection volume"); _finite(self.minimum_distance_mm,"minimum distance")
        if self.intersection_volume_mm3!=0.0: raise DrySidePackageError(f"required-clear dry-side collision: {self.check_id}")
    def manifest(self): return {"check_id":self.check_id,"first_id":self.first_id,"second_id":self.second_id,"intersection_volume_mm3":self.intersection_volume_mm3,"minimum_distance_mm":self.minimum_distance_mm,"passes":True}

@dataclass(frozen=True,slots=True)
class DrySidePackage:
    authority_revision:str; physical_geometry:tuple[PackageGeometry,...]; reference_geometry:tuple[PackageGeometry,...]; service_geometry:tuple[PackageGeometry,...]; collision_checks:tuple[CollisionCheck,...]; pcb_mounting_datums_xyz_mm:tuple[tuple[float,float,float],...]; battery_nominal_voltage_V:float; battery_capacity_mAh:float; battery_mass_g:float; rib_ratio:float
    def __post_init__(self):
        if self.authority_revision!=AUTHORITY_REVISION: raise DrySidePackageError("authority revision mismatch")
        ids=[i.geometry_id for i in (*self.physical_geometry,*self.reference_geometry,*self.service_geometry)]
        if len(ids)!=len(set(ids)): raise DrySidePackageError("dry-side geometry IDs cannot repeat")
        if len(self.physical_geometry)!=1 or self.physical_geometry[0].geometry_id!="DRY_BAY_CARRIER_STRUCTURE": raise DrySidePackageError("Cell 12 physical material must be only the internal carrier structure")
        if any(i.material_class!="PHYSICAL_MATERIAL_CANDIDATE" for i in self.physical_geometry): raise DrySidePackageError("physical set contains non-material geometry")
        if any(i.material_class=="PHYSICAL_MATERIAL_CANDIDATE" for i in (*self.reference_geometry,*self.service_geometry)): raise DrySidePackageError("reference/service geometry cannot silently enter material")
        if len(self.pcb_mounting_datums_xyz_mm)!=4: raise DrySidePackageError("PCB zone requires four deterministic mounting datums")
        for point in self.pcb_mounting_datums_xyz_mm: _point(point,"PCB mounting datum")
        for value,label in ((self.battery_nominal_voltage_V,"battery nominal voltage"),(self.battery_capacity_mAh,"battery capacity"),(self.battery_mass_g,"battery mass"),(self.rib_ratio,"rib ratio")): _finite(value,label,positive=True)
    @property
    def package_sha256(self): return sha256(json.dumps(self.manifest(False),sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    def manifest(self,include_sha=True):
        unresolved="BLOCKED_PENDING_SELECTED_HARDWARE_OR_CONTROLLED_SUPPLIER_OR_MEASUREMENT_EVIDENCE"
        payload={"schema":SCHEMA,"authority_revision":self.authority_revision,"world_frame_id":WORLD_FRAME_ID,"dry_bay_local_frame":{"frame_id":LOCAL_FRAME_ID,"parent_frame_id":WORLD_FRAME_ID,"origin_in_parent_mm":list(DRY_BAY_CENTER_MM),"x_axis_in_parent":[1.0,0.0,0.0],"y_axis_in_parent":[0.0,1.0,0.0],"z_axis_in_parent":[0.0,0.0,1.0],"transform_semantics":"IDENTITY_ROTATION_PLUS_EXPLICIT_WORLD_TRANSLATION_MM"},"sources":{"main_sha":SOURCE_MAIN_SHA,"source_git_blobs":{p:d for p,d in SOURCE_GIT_BLOB_IDENTITIES},"legacy_donor_pr":LEGACY_DONOR_PR,"legacy_donor_head_sha":LEGACY_DONOR_HEAD_SHA,"legacy_donor_electronics_blob_sha":LEGACY_DONOR_BLOB_SHA,"donor_semantics":"CONCEPT_AND_LABELLED_CAD_RESERVATION_SEEDS_ONLY_NOT_AUTHORITY"},"physical_geometry":[i.manifest() for i in self.physical_geometry],"reference_geometry":[i.manifest() for i in self.reference_geometry],"service_geometry":[i.manifest() for i in self.service_geometry],"pcb_mounting_datums_xyz_mm":[list(p) for p in self.pcb_mounting_datums_xyz_mm],"power_ledger":{"battery_nominal_voltage_V":self.battery_nominal_voltage_V,"battery_capacity_mAh":self.battery_capacity_mAh,"battery_mass_g":self.battery_mass_g,"loads":[{"load_id":lid,"quantity":q,"nominal_power_W":None,"status":unresolved} for lid,q in zip(LOAD_IDS,(4,1,1,1,1,1),strict=True)],"total_dry_side_mass_g":None,"total_power_W":None,"runtime_estimate_h":None,"runtime_validated":False},"collision_checks":[i.manifest() for i in self.collision_checks],"interfaces":{"frame_attachment":{"datum_xyz_mm":[0.0,0.0,-25.0],"relationship":"POSITIVE_ATTACHMENT_REQUIRED_COUNTERPART_UNRELEASED","status":"BLOCKED_RELEASED_FRAME_HAS_TOPOLOGY_ONLY_NO_3D_DRY_BAY_COUNTERPART"},"rear_service_closure":{"owner":"CELL2_EXTERIOR","interface_datum_xyz_mm":[0.0,0.0,-47.0],"relationship":"SEAL_INTERFACE_RESERVATION_AND_POSITIVE_CLOSURE_COUNTERPART_REQUIRED","cell12_visible_door_material_exists":False,"status":"BLOCKED_EXTERIOR_COVER_ATTACHMENT_SEAL_STACK_AND_INGRESS_UNSELECTED"},"charging":{"datum_xyz_mm":list(CHARGE_CENTER_MM),"axis_xyz":[-1.0,0.0,0.0],"relationship":"SEAL_INTERFACE_RESERVATION","status":"CONNECTOR_TYPE_RETENTION_INGRESS_CERTIFICATION_AND_ACTIVE_WET_CHARGING_UNSELECTED"},"hmi_thermal_electrical_handoff":{"owner":"CELL14_HMI_THERMAL","datum_xyz_mm":None,"relationship":"ELECTRICAL_INTERFACE_REQUIRED","status":"BLOCKED_PCB_EDGE_CONNECTOR_HARNESS_ROUTING_AND_COMPONENT_PLACEMENT_UNSELECTED"}},"service_sequence":{"battery_removal":["DEVICE_REMOVED_FROM_WEARER_AND_UNPOWERED","CELL2_EXTERIOR_REAR_COVER_REMOVED","BATTERY_DISCONNECTED_BY_UNSELECTED_SAFE_CONNECTOR_SEQUENCE","BATTERY_WITHDRAWN_ALONG_CELL12_REARWARD_SERVICE_SWEEP"],"physical_service_validated":False},"dfm":{"dry_bay_wall_mm":DRY_BAY_WALL_MM,"battery_guide_wall_mm":BATTERY_GUIDE_WALL_MM,"support_rib_thickness_mm":SUPPORT_RIB_THICKNESS_MM,"support_rib_to_wall_ratio":self.rib_ratio,"draft_geometry_realized":False,"draft_status":"BLOCKED_DRAFT_AND_PARTING_ARCHITECTURE_NOT_YET_REALIZED","material_status":"UNSELECTED","tolerance_stack_status":"PROVISIONAL_DIGITAL_CLEARANCES_ONLY"},"integration":{"frame_positive_attachment_realized":False,"cell12_visible_door_material_exists":False,"exterior_closure_positive_attachment_realized":False,"charging_connector_selected":False,"ingress_validated":False,"electrical_safety_validated":False,"development_assembly_status":"REVIEW_ONLY_NOT_INSERTED_INTO_RELEASED_PHYSICAL_ASSEMBLY"},"evidence_status":EVIDENCE_STATUS}
        if include_sha: payload["package_sha256"]=self.package_sha256
        return payload

def _z_sweep(size,start,end_z):
    sx,sy,sz=size
    if end_z>=start[2]: raise DrySidePackageError("rear service sweep must travel along -Z")
    return _box((sx,sy,sz+start[2]-end_z),(start[0],start[1],(start[2]+end_z)/2.0))

def _build_geometry(authority):
    bw,bh,bd=tuple(float(i) for i in authority.get("battery_reference","envelope_mm"))
    outer=_rounded_box_xy(DRY_BAY_OUTER_MM,DRY_BAY_CENTER_MM,8.0)
    inner=_rounded_box_xy((DRY_BAY_OUTER_MM[0]-2*DRY_BAY_WALL_MM,DRY_BAY_OUTER_MM[1]-2*DRY_BAY_WALL_MM,DRY_BAY_OUTER_MM[2]-2*DRY_BAY_WALL_MM),DRY_BAY_CENTER_MM,6.2)
    shell=outer.cut(inner)
    support=_box(PCB_SUPPORT_MM,PCB_SUPPORT_CENTER_MM)
    guide_left=_box((BATTERY_GUIDE_WALL_MM,bh+2*BATTERY_FAULT_CLEARANCE_XY_MM,bd+2*BATTERY_FAULT_CLEARANCE_Z_MM),(BATTERY_CENTER_MM[0]-(bw/2+BATTERY_FAULT_CLEARANCE_XY_MM+BATTERY_GUIDE_WALL_MM/2),BATTERY_CENTER_MM[1],BATTERY_CENTER_MM[2]))
    guide_right=_box((BATTERY_GUIDE_WALL_MM,bh+2*BATTERY_FAULT_CLEARANCE_XY_MM,bd+2*BATTERY_FAULT_CLEARANCE_Z_MM),(BATTERY_CENTER_MM[0]+(bw/2+BATTERY_FAULT_CLEARANCE_XY_MM+BATTERY_GUIDE_WALL_MM/2),BATTERY_CENTER_MM[1],BATTERY_CENTER_MM[2]))
    structure=shell.union(support).union(guide_left).union(guide_right)
    battery=_box((bw,bh,bd),BATTERY_CENTER_MM)
    fault=_box((bw+2*BATTERY_FAULT_CLEARANCE_XY_MM,bh+2*BATTERY_FAULT_CLEARANCE_XY_MM,bd+2*BATTERY_FAULT_CLEARANCE_Z_MM),BATTERY_CENTER_MM)
    pcb=_box(PCB_REFERENCE_MM,PCB_CENTER_MM)
    power=_box(POWER_ZONE_MM,POWER_ZONE_CENTER_MM)
    charge=_box(CHARGE_RESERVATION_MM,CHARGE_CENTER_MM)
    closure=_rounded_box_xy(CLOSURE_INTERFACE_MM,CLOSURE_INTERFACE_CENTER_MM,CLOSURE_INTERFACE_CORNER_RADIUS_MM)
    sweep=_z_sweep((bw+2*BATTERY_FAULT_CLEARANCE_XY_MM,bh+2*BATTERY_FAULT_CLEARANCE_XY_MM,bd+2*BATTERY_FAULT_CLEARANCE_Z_MM),BATTERY_CENTER_MM,BATTERY_SERVICE_END_Z_MM)
    return structure,battery,fault,pcb,power,charge,closure,sweep

def build_dry_side_package(authority=None,model=None):
    _require_sources(); authority=load_authority() if authority is None else authority; _require_authority(authority)
    model=build_model(authority) if model is None else model
    if type(model) is not MasckOneModel: raise DrySidePackageError("dry-side package requires exact MasckOneModel type")
    structure,battery,fault,pcb,power,charge,closure,sweep=_build_geometry(authority)
    physical=(PackageGeometry("DRY_BAY_CARRIER_STRUCTURE","internal dry-side carrier shell, PCB shelf and battery guide structure",structure,"PHYSICAL_MATERIAL_CANDIDATE","DRY_ALWAYS","DIGITAL_BREP_CANDIDATE"),)
    refs=(PackageGeometry("BATTERY_PACKAGING_BENCHMARK","authority battery packaging benchmark",battery,"REFERENCE_ONLY","DRY_ALWAYS","AUTHORITY_REFERENCE_NOT_PRODUCTION_FREEZE"),PackageGeometry("BATTERY_FAULT_CLEARANCE_RESERVATION","noncompressive battery fault clearance reservation",fault,"REFERENCE_ONLY","DRY_ALWAYS","CAD_RESERVATION_SEED_NOT_SUPPLIER_REQUIREMENT"),PackageGeometry("PCB_BARE_BOARD_REFERENCE","reflowed PCB bare-board packaging reference",pcb,"REFERENCE_ONLY","DRY_ALWAYS","PCB_COMPONENTS_AND_ROUTING_UNSELECTED"),PackageGeometry("PCB_POWER_PROTECTION_CHARGING_ZONE","PCB power/protection/charging placement zone",power,"REFERENCE_ONLY","DRY_ALWAYS","COMPONENTS_UNSELECTED"),PackageGeometry("CHARGING_WALL_CROSSING_SEAL_RESERVATION","charging wall-crossing and seal reservation",charge,"SEAL_INTERFACE_RESERVATION","WET_DRY_BOUNDARY","CONNECTOR_UNSELECTED"),PackageGeometry("REAR_CLOSURE_SEAL_INTERFACE_RESERVATION","Cell 2 rear-cover seal interface reservation",closure,"SEAL_INTERFACE_RESERVATION","WET_DRY_BOUNDARY","VISIBLE_COVER_EXTERNALLY_OWNED"))
    services=(PackageGeometry("BATTERY_REARWARD_SERVICE_SWEEP","continuous battery plus fault-clearance rearward withdrawal sweep",sweep,"SERVICE_SWEEP_REFERENCE","DRY_ALWAYS","DIGITAL_SERVICE_SWEEP_ONLY"),)
    released=(("rigid_shell",model.rigid_shell),*((f"actuator_envelope_{i+1}",s) for i,s in enumerate(model.actuator_envelopes)),("water_reservoir_envelope",model.water_reservoir_envelope),("waste_cartridge_envelope",model.waste_cartridge_envelope),("battery_reference_envelope",model.battery_reference_envelope),*((f"visual_{k}",v) for k,v in model.protected_visuals.items()))
    checks=[]
    for first_id,first in ((physical[0].geometry_id,structure),(services[0].geometry_id,sweep)):
        for second_id,second in released:
            checks.append(CollisionCheck(f"{first_id}__CLEAR_OF__{second_id}",first_id,second_id,_intersection(first,second),_distance(first,second)))
    pcb_datums=((-16.0,10.0,-29.4),(16.0,10.0,-29.4),(-16.0,28.0,-29.4),(16.0,28.0,-29.4))
    low,high=authority.get("manufacturing","rib_thickness_ratio_range"); ratio=SUPPORT_RIB_THICKNESS_MM/DRY_BAY_WALL_MM
    if not float(low)<=ratio<=float(high): raise DrySidePackageError("support rib ratio outside authority baseline")
    return DrySidePackage(AUTHORITY_REVISION,physical,refs,services,tuple(checks),pcb_datums,authority.number("battery_reference","nominal_voltage_V"),authority.number("battery_reference","capacity_mAh"),authority.number("battery_reference","mass_g"),ratio)
