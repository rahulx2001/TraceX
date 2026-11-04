import json
import re
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

# Load original sample and reviews
sample_path = Path('/Users/rahulkumarsinghj/DeveloperFolder/Code/v2_ai_rca_tool_ml-score-improvement/reports/defect/defect_label_sample_300.csv')
orig_json_path = Path('/Users/rahulkumarsinghj/Downloads/defect-review (3).json')

sample_df = pd.read_csv(sample_path)
with open(orig_json_path, 'r') as f:
    orig_data = json.load(f)

orig_reviews = {r['sample_id']: r for r in orig_data['reviews']}

# The 31 grounded disagreements
disagreements = {
    'S004': {
        'label': 'other_unclear',
        'notes': 'The narrative describes only an intermittent SRS warning light illuminating approximately once per week during driving, with no crash event, dealer diagnosis, or confirmed restraint module hardware failure. Under Rule 3, generic warning indicators without diagnostic confirmation do not support a specific component defect; categorized as other/unclear.'
    },
    'S007': {
        'label': 'other_unclear',
        'notes': 'The complaint provides a single-sentence report stating only that the backup camera is intermittent. There is no diagnostic record, dealership inspection, or evidence attributing the issue to software rather than camera wiring, loose connectors, or hardware failure. Categorized as other/unclear under Rule 3.'
    },
    'S016': {
        'label': 'other_unclear',
        'notes': 'The complaint describes engine hesitation/bogging when accelerating under load or on inclines following recall repairs. No complete engine stalling occurred, and there is no diagnostic evidence implicating a relay defect. An unresolved drivability symptom under load cannot be presumed to be relay_stall; categorized as other/unclear.'
    },
    'S017': {
        'label': 'instrument_cluster_panel_compliance_or_label',
        'notes': 'The complainant describes the fuel gauge and cluster glitching and failing depending on weather conditions, obscuring remaining fuel volume and mileage. This represents a functional display failure of the instrument cluster panel, rather than a wiring defect.'
    },
    'S028': {
        'label': 'other_unclear',
        'notes': 'The complaint reports illumination of the power steering warning light accompanied solely by the owner\'s conjecture of possible water penetration from heavy rain. With no technical inspection, dealer diagnosis, or confirmed wiring harness fault, a warning light alone must be classified as other/unclear.'
    },
    'S034': {
        'label': 'other_unclear',
        'notes': 'The owner received a recall notification regarding the Hydraulic Electronic Control Unit (HECU) with parts not yet available. No fire, malfunction, or failure was actually experienced in the vehicle. Under Rule 2, a recall notification alone without an actual failure is insufficient, and HECU is not wiring; categorized as other/unclear.'
    },
    'S036': {
        'label': 'other_unclear',
        'notes': 'The vehicle stalled intermittently on the highway and was serviced by replacing the crankshaft position sensor. Because crankshaft sensors are engine sensors outside the frozen electrical system taxonomy, and no relay defect was identified, this intermittent stall is categorized as other/unclear.'
    },
    'S038': {
        'label': 'other_unclear',
        'notes': 'The narrative provides an unverified assertion that an electrical system failure caused the vehicle to enter a ditch, alongside allegations of third-party tampering. Absent any documented dealership diagnosis confirming a wiring harness fault, this ambiguous report falls under other/unclear.'
    },
    'S041': {
        'label': 'other_unclear',
        'notes': 'The complaint alleges that daytime running lights (DRLs) in the quad-beam headlamp assemblies burn out continuously. DRL bulb/LED failure is an exterior lighting hardware issue rather than a wiring defect within the electrical system taxonomy; categorized as other/unclear.'
    },
    'S044': {
        'label': 'other_unclear',
        'notes': 'The vehicle unexpectedly braked to a complete stop from 40 mph with an unresponsive accelerator pedal. This represents an active collision mitigation/ESC system malfunction rather than a compliance certification or labeling defect; categorized as other/unclear.'
    },
    'S046': {
        'label': 'other_unclear',
        'notes': 'An independent mechanic diagnosed a seized mechanical brake caliper causing severe vibration and rotor overheating. Mechanical brake caliper seizure is a foundation brake defect, not an ESC compliance or labeling defect; categorized as other/unclear.'
    },
    'S048': {
        'label': 'engine_and_engine_cooling_leak',
        'notes': 'The dealership diagnosed coolant intrusion into cylinder 2 on this 2.0L EcoBoost engine, necessitating short block replacement. Coolant leaking into cylinders constitutes an internal engine coolant leak rather than a missing or incorrect component.'
    },
    'S070': {
        'label': 'other_unclear',
        'notes': 'The owner experienced a sudden power loss at highway speed and noticed rising temperature gauge readings, speculating an Integrated Thermal Management System (ITMS) fault. However, the vehicle had not been diagnosed or inspected by a technician at the time of submission. Unverified owner theories default to other/unclear.'
    },
    'S078': {
        'label': 'belts_and_associated_pulleys_detachment',
        'notes': 'The vehicle experienced low oil pressure warning illumination and motive power loss under NHTSA Recall 23V905000. This recall directly addresses fracture and detachment of the oil pump drive belt tensioner arm and belt degradation. Consistent with S079 and S080, this failure maps to belts_and_associated_pulleys_detachment.'
    },
    'S084': {
        'label': 'other_unclear',
        'notes': 'The complaint cites Ford TSB 23-2143 regarding worn variable camshaft timing (VCT) units and stretched timing chains causing cold start rattles and auto-restart issues. VCT phaser wear and timing chain stretching do not represent missing/wrong parts and lie outside the engine defect taxonomy; categorized as other/unclear.'
    },
    'S190': {
        'label': 'other_unclear',
        'notes': 'The entire narrative consists solely of the phrase "Seat belt fault". No specific buckle, retractor, anchor, or compliance failure mode is documented. Under Rule 3, such brevity and absence of evidence requires an other/unclear classification.'
    },
    'S198': {
        'label': 'other_unclear',
        'notes': 'The owner received a recall notice for NHTSA Campaign 22V056000 (HECU internal brake fluid leak/fire risk) but experienced no vehicle failure or symptom. Under Rule 2, a recall notification alone without an actual failure is insufficient; categorized as other/unclear.'
    },
    'S201': {
        'label': 'other_unclear',
        'notes': 'The complaint reports that the brake pedal dropped completely to the floor while stationary at a traffic signal. Total loss of hydraulic pedal resistance reflects a hydraulic or master cylinder failure, not a regulatory compliance or labeling defect; categorized as other/unclear.'
    },
    'S203': {
        'label': 'other_unclear',
        'notes': 'Upon startup, multiple dashboard warning lights illuminated simultaneously (ABS, steering, FCW, LDW, Brake) without any drivability incident or diagnostic confirmation of an ABS/ESC software bug. Multi-lamp warning illumination without dealer diagnosis defaults to other/unclear.'
    },
    'S215': {
        'label': 'other_unclear',
        'notes': 'The complaint describes severe steering oscillation ("death wobble") at highway speeds, with repairs including the steering damper, track bar, and steering box. Because no tie rod assembly failure or separation was identified, this solid-axle dynamic oscillation is categorized as other/unclear.'
    },
    'S216': {
        'label': 'other_unclear',
        'notes': 'The vehicle suffered a total electrical and powertrain blackout at 65 mph, resulting in an expected secondary loss of power steering assist. Because the primary root failure was a complete vehicle shutdown rather than an isolated EPAS motor/gear defect, it is categorized as other/unclear under steering.'
    },
    'S230': {
        'label': 'other_unclear',
        'notes': 'The owner discovered water leaking onto the driver\'s side floorboard and soaking the carpet. Interior water intrusion from weatherstripping or body seams is not a body structure compliance or labeling defect; categorized as other/unclear.'
    },
    'S231': {
        'label': 'other_unclear',
        'notes': 'The power sliding door failed to reverse when encountering an obstacle, closing onto an occupant. Failure of the anti-pinch obstacle detection system is a sensor/motor logic fault, not a physical door hinge or attachment detachment; categorized as other/unclear.'
    },
    'S234': {
        'label': 'other_unclear',
        'notes': 'The owner reports noticeable hood flutter and vibration causing distracting light reflections at highway speeds. Hood panel vibration is unrelated to roof and pillar structural integrity; categorized as other/unclear.'
    },
    'S236': {
        'label': 'other_unclear',
        'notes': 'The right rear passenger door will not unlock or open from either the inside or outside handle. A jammed door lock actuator or mechanical latch mechanism is an unlisted latch hardware defect, not a door compliance or label nonconformity; categorized as other/unclear.'
    },
    'S237': {
        'label': 'hinge_and_attachments_detachment',
        'notes': 'The driver\'s door produces popping/cracking noises upon opening, and the window cannot roll down completely because the internal door check/hinge spot weld has broken away. Consistent with S232 and S239, this constitutes hinge_and_attachments_detachment.'
    },
    'S246': {
        'label': 'other_unclear',
        'notes': 'The complainant reports persistent slow pressure loss in the right rear tire over six months, with pressure fluctuations linked to ambient weather. Gradual air seepage or bead leaks do not constitute a tire compliance or labeling defect; categorized as other/unclear.'
    },
    'S247': {
        'label': 'other_unclear',
        'notes': 'A dealership technician pointed out uneven tire tread wear during routine maintenance, but no mechanical diagnosis or suspension repair was undertaken. Irregular tire wear without proven tire manufacturing defects is categorized as other/unclear.'
    },
    'S248': {
        'label': 'other_unclear',
        'notes': 'The complaint describes highway-speed vehicle vibration and humming, diagnosed by the dealership as excessive tire road force variation leading to tire replacement. Road force imbalance is not a tire compliance or labeling defect; categorized as other/unclear.'
    },
    'S293': {
        'label': 'other_unclear',
        'notes': 'The complainant asserts that the windshield wiper motor runs too slowly and intermittently stops in heavy rain, referencing wiper motor mechanical recalls. Mechanical or electrical motor insufficiency is not a wiper software defect; categorized as other/unclear.'
    },
    'S300': {
        'label': 'other_unclear',
        'notes': 'The complainant reports swollen two-piece capped wheel lug nuts that could not be removed during routine tire service, requiring replacement with solid one-piece nuts. Swelling of sheet-metal lug caps is not cracking or fracturing of the lug studs; categorized as other/unclear.'
    }
}

print('Disagreements defined:', len(disagreements))
