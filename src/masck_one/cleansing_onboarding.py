"""One canonical, renderable onboarding contract; not a validated questionnaire."""
from dataclasses import dataclass, asdict

VERSION='MASCK_CLEANSING_ONBOARDING_2'

@dataclass(frozen=True)
class Question:
    id: str
    prompt: str
    answer_family: str
    regional: bool
    variable: str
    period: str
    purpose: str
    distinction: str
    section: str
    help: str='Choose what you notice; you do not need to know your skin type.'

QUESTIONS=(
 Question('usual_oil','Between washes, how shiny or greasy does each area usually become?','LEVEL',True,'baseline_oil','USUAL','Retain usual oil tendency separately from today.','Not current product film or current shine.','Usual experience'),
 Question('usual_dry','After your usual wash, how much does each area feel tight or stretched?','LEVEL',True,'baseline_dry','USUAL','Retain the usual post-wash tightness tendency.','Not current discomfort; can coexist with oil.','Usual experience'),
 Question('current_oil','How shiny or greasy does each area feel right now?','LEVEL',True,'current_oil','NOW','Compare with a pre-wet surface-oil observation.','Usual tendency is not a current measurement.','Right now'),
 Question('current_dry','How tight or stretched does each area feel right now?','LEVEL',True,'current_dry','NOW','Compare with a qualified current surface observation.','Not a skin-type label or disease assessment.','Right now'),
 Question('flaking_now','Have you noticed small flakes on any area today?','YES_NO',True,'dryness_caution','NOW','Preserve a concrete caution alongside tightness.','Flakes and tightness need not occur together.','Right now'),
 Question('water_stings','When water last touched these areas, did any sting or feel uncomfortable?','YES_NO',True,'contact_concern','HISTORY_WINDOW','Require review of reported contact discomfort.','A specific contact trigger, not a diagnosis.','Comfort'),
 Question('product_reactivity','Have products you normally tolerate caused stinging or discomfort?','YES_NO',True,'sensitivity_history','HISTORY_WINDOW','Retain reported reactivity even if a reading looks ordinary.','Historical product response differs from discomfort now.','Comfort'),
 Question('discomfort_now','Before starting, does any area feel sore, stinging or uncomfortable?','YES_NO',True,'current_concern','NOW','Current concern or uncertainty requires review before contact.','Catches present discomfort without a known trigger.','Comfort'),
 Question('recent_cleanse','Have you already washed your face during the period shown above?','YES_NO',False,'recent_burden','HISTORY_WINDOW','Identify cleansing absent from a device record.','One event differs from repeated events.','Recent care'),
 Question('multiple_cleanses','Have you washed your face more than once during that same period?','YES_NO',False,'repeat_burden','HISTORY_WINDOW','Identify repetition; cannot negate a reported single wash.','Checked against the preceding answer.','Recent care'),
 Question('exfoliation','Have you used a scrub, exfoliating product, brush or similar tool during that period?','YES_NO',True,'surface_stress','HISTORY_WINDOW','Retain recent additional surface-action burden.','Chemical and mechanical products are both included.','Recent care','Include products described on their label as exfoliating. Choose not sure if you cannot tell.'),
 Question('hair_removal','Have you shaved or removed hair from any of these areas during that period?','YES_NO',True,'hair_removal_stress','HISTORY_WINDOW','Retain local recent surface disturbance.','Having facial hair is a different question.','Recent care'),
 Question('other_stress','Has rubbing or exposure to your surroundings left any area uncomfortable during that period?','YES_NO',True,'other_surface_stress','HISTORY_WINDOW','Catch surface discomfort not explained by the preceding events.','Not a request to rate environmental danger.','Recent care'),
 Question('product_film','Is any product still on these areas, such as moisturiser, sunscreen or makeup?','YES_NO',True,'measurement_film','NOW','Qualify what a sensor may be observing.','Product presence is not product identity.','Before the reading'),
 Question('changed_product','Is the cleanser different from the one confirmed for this prepared session?','YES_NO',False,'product_binding_change','SESSION','Request the canonical preparation check after a change.','Does not identify or recommend a product.','Before the reading','The prepared cleanser name must be shown. If it is unavailable, this answer remains unknown.'),
 Question('wet_or_sweaty','Are any of these areas wet or sweaty right now?','YES_NO',True,'measurement_wetness','NOW','Invalidate a dry-phase observation when conditions differ.','Sweat cannot be interpreted as oil or hydration.','Before the reading'),
 Question('environment_changed','Have your surroundings changed noticeably since your earlier answers or reading?','YES_NO',False,'context_change','SESSION','Ask for current evidence after a context change.','Context is not a reason for stronger cleansing.','Before the reading'),
 Question('left_right_difference','Do matching areas on the left and right feel different today?','YES_NO',False,'regional_asymmetry','NOW','Require local answers instead of copying a face-wide answer.','This is not a diagnosis or appearance comparison.','Regional detail'),
 Question('hair_obstruction','Is there facial hair where a contact surface would need to sit?','YES_NO',True,'placement_obstruction','NOW','Pass contact uncertainty to placement verification.','Separate from recent shaving.','Regional detail'),
 Question('answer_confidence','Do these answers describe what you can notice confidently?','YES_NO',False,'survey_clarity','NOW','Retain uncertainty instead of guessing.','Per-answer uncertainty remains available.','Review'),
)


def form_contract(*,history_window_label=None,prepared_cleanser_label=None):
    """UI-ready data, including explicit missing context and per-answer uncertainty."""
    items=[]
    for q in QUESTIONS:
        row=asdict(q)
        if q.answer_family=='LEVEL':
            choices=[('LOW','None or very little'),('MODERATE','Some'),('HIGH','A lot'),('UNKNOWN',"I'm not sure")]
        else:choices=[('YES','Yes'),('NO','No'),('UNKNOWN',"I'm not sure")]
        row['choices']=[{'value':v,'label':label} for v,label in choices]
        row['initial_value']=None
        row['allow_per_answer_uncertainty']=True
        row['context_available']=bool(history_window_label) if q.period=='HISTORY_WINDOW' else bool(prepared_cleanser_label) if q.id=='changed_product' else True
        row['regional_ui']='Start with a face-wide answer; expand named regions if they differ.' if q.regional else 'One answer'
        row['unknown_effect']='Preserve uncertainty; never substitute NO or LOW.'
        items.append(row)
    return {'version':VERSION,'status':'CONTENT_SELECTED_USABILITY_AND_DISCRIMINATION_UNVALIDATED',
        'intro':'Tell Masck what you notice. You do not need to know your skin type.',
        'history_window_label':history_window_label,'prepared_cleanser_label':prepared_cleanser_label,
        'history_window_is_a_qualified_upstream_input':True,'questions':items,
        'no_preselected_answers':True,'demographic_inputs':[],
        'per_answer_confidence_options':['CERTAIN','UNSURE','UNKNOWN'],
        'accessibility':['Named regions in text','No colour-only meaning','No image recognition required'],
        'future_inputs_cannot_supply_operating_limits':True}


def interpret_form(payload, *, regions, history_window_label=None, prepared_cleanser_label=None):
    """Strict UI boundary. Context-free history/product answers are never actionable.

    Labels are supplied by the qualified session/history owner, not chosen here.
    No profile, community template, demographic field or proposed limit is input.
    """
    from .regional_cleansing import Answers, ControlError
    if set(payload)-{'version','global_values','regional_values','per_answer_confidence'}:
        raise ControlError('unsupported onboarding input')
    if payload.get('version')!=VERSION:raise ControlError('onboarding version mismatch')
    global_values=dict(payload.get('global_values',{}))
    local={r:dict(v) for r,v in payload.get('regional_values',{}).items()}
    clarity=dict(payload.get('per_answer_confidence',{}))
    Answers(global_values,local,clarity).validate(regions)
    form=form_contract(history_window_label=history_window_label,prepared_cleanser_label=prepared_cleanser_label)
    for q in form['questions']:
        if not q['context_available']:
            global_values[q['id']]='UNKNOWN'
            for values in local.values():
                if q['id'] in values:values[q['id']]='UNKNOWN'
    return Answers(global_values,local,clarity)
