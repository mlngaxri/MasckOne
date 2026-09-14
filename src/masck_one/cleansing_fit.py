"""Explicit geometric study-envelope selection, not anthropometric fit validation."""
from dataclasses import dataclass
from typing import Mapping
from .regional_cleansing import ControlError, finite

DIMENSIONS=('face_width','face_length','forehead_projection','cheek_left_projection',
 'cheek_right_projection','nose_projection','nose_width','chin_projection',
 'jaw_width','left_right_asymmetry','local_curvature_radius')

@dataclass(frozen=True)
class FitStudy:
    size_id: str
    bounds_mm: Mapping[str,tuple[float,float]]
    registration_digest: str
    supported_hair_states: frozenset[str]

    def matches(self,dimensions,hair_state):
        if set(self.bounds_mm)!=set(DIMENSIONS):raise ControlError('incomplete morphology envelope')
        if set(dimensions)!=set(DIMENSIONS):return False
        if len(self.registration_digest)!=64:raise ControlError('registration evidence identity required')
        if hair_state not in self.supported_hair_states:return False
        for key,(lo,hi) in self.bounds_mm.items():
            finite(lo,key);finite(hi,key);finite(dimensions[key],key)
            if lo>hi:raise ControlError('reversed morphology bounds')
            if not lo<=dimensions[key]<=hi:return False
        return True


def select_study(dimensions,hair_state,catalogue=()):
    matches=[c.size_id for c in catalogue if c.matches(dimensions,hair_state)]
    return {'matching_studies':matches,'status':'GEOMETRIC_STUDY_MATCH' if matches else 'UNSUPPORTED_OR_UNREGISTERED',
            'human_fit_validated':False,'human_use_eligible':False}
