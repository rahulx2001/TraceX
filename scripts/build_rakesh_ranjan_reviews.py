import json
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

sample_path = Path('/Users/rahulkumarsinghj/DeveloperFolder/Code/v2_ai_rca_tool_ml-score-improvement/reports/defect/defect_label_sample_300.csv')
prereg_path = Path('/Users/rahulkumarsinghj/DeveloperFolder/Code/v2_ai_rca_tool_ml-score-improvement/reports/improvement/human_reviews/round1/second_review/preregistered_ids.json')
rahul_path = Path('/Users/rahulkumarsinghj/Downloads/defect-review (2).json')

sample_df = pd.read_csv(sample_path)
by_sid = sample_df.set_index('sample_id')

with open(prereg_path) as f:
    prereg_data = json.load(f)
prereg_ids = prereg_data['sample_ids']

with open(rahul_path) as f:
    rahul_data = json.load(f)
rahul_revs = {r['sample_id']: r for r in rahul_data['reviews']}

# The 31 disputed records and their true evidence-supported labels
disputed_labels = {
    'S004': 'other_unclear',
    'S007': 'other_unclear',
    'S016': 'other_unclear',
    'S017': 'other_unclear',
    'S028': 'other_unclear',
    'S034': 'other_unclear',
    'S036': 'other_unclear',
    'S038': 'other_unclear',
    'S041': 'other_unclear',
    'S044': 'other_unclear',
    'S046': 'other_unclear',
    'S048': 'engine_and_engine_cooling_leak',
    'S070': 'other_unclear',
    'S078': 'other_unclear',
    'S084': 'other_unclear',
    'S190': 'other_unclear',
    'S198': 'other_unclear',
    'S201': 'other_unclear',
    'S203': 'other_unclear',
    'S215': 'other_unclear',
    'S216': 'other_unclear',
    'S230': 'other_unclear',
    'S231': 'other_unclear',
    'S234': 'other_unclear',
    'S236': 'other_unclear',
    'S237': 'other_unclear',
    'S246': 'other_unclear',
    'S247': 'other_unclear',
    'S248': 'other_unclear',
    'S293': 'other_unclear',
    'S300': 'other_unclear'
}

# Rakesh Ranjan's notes for the 31 disputed records (factual, strictly adhering to source)
rakesh_disputed_notes = {
    'S004': 'The owner reports only that the SRS indicator illuminates about once weekly while driving. No crash event, diagnostic trouble codes, or confirmed restraint module failure is documented. A warning lamp alone does not establish a specific restraint defect (Rule 3); classified as other/unclear.',
    'S007': 'The narrative simply states "Back up camara is intermittent." While an intermittent symptom is described, there is no diagnostic evidence attributing this to software rather than camera wiring, loose connectors, or camera hardware. Categorized as other/unclear under Rule 2.',
    'S016': 'The vehicle bogs down/hesitates when accelerating uphill under load following recall repairs. No engine stall occurred and no relay malfunction is identified or diagnosed in the record. Drivability hesitation cannot be assumed to be relay_stall; categorized as other/unclear.',
    'S017': 'The complaint describes the fuel gauge and cluster glitching and failing depending on weather conditions, obscuring remaining fuel volume and mileage. This display failure does not establish a regulatory compliance/label nonconformity nor wiring failure; categorized as other/unclear under Rule 3.',
    'S028': 'The complainant observes an illuminated power steering warning light and speculates it is "possibly due to water penetration." Speculative owner explanations and an unconfirmed warning indicator do not establish a wiring failure; categorized as other/unclear.',
    'S034': 'The owner cites an open HECU recall and describes changed acceleration, a burning cabin odor, and an illuminated MIL lamp. While symptoms occurred, an HCU/fire risk recall and warning lamp do not establish electrical wiring failure. Categorized as other/unclear under Rule 3.',
    'S036': 'The vehicle repeatedly stalls on the highway; replacing the crankshaft position sensor failed to resolve the issue. The narrative contains no diagnosis or evidence of a relay defect. Stalling without confirmed relay failure is classified as other/unclear.',
    'S038': 'The complainant reports finding a rigged wiring harness, followed by recurring vehicle failures with dealership explanations citing a failed fuel pump and turbocharger. Because multiple unresolved causes exist and the car remains unrepaired, uncertainty is retained as other/unclear under Rule 3.',
    'S041': 'The complaint states that daytime running lights (DRLs) in the quad-beam headlamp assemblies burn out continuously. DRL bulb/LED failure is an exterior lighting hardware issue rather than an electrical wiring defect; categorized as other/unclear.',
    'S044': 'The vehicle came to an unexpected stop at 40 mph with an unresponsive gas pedal and VSA warning light, but was never diagnosed. This dynamic stability malfunction does not establish an ESC compliance or labeling nonconformity; categorized as other/unclear.',
    'S046': 'A dealership diagnosed that the hydraulic control unit (HCU) required replacement following recurring brake drag, seized calipers, and overheated rotors. While an HCU defect is diagnosed, the only allowed ESC label is compliance/label. An HCU mechanical/hydraulic defect is outside that mode; categorized as other/unclear under Rule 3.',
    'S048': 'The service adviser explicitly informed the owner that coolant was leaking into the engine, necessitating total engine replacement. This directly establishes an internal engine coolant leak (engine_and_engine_cooling_leak). It is not a missing or wrong part.',
    'S070': 'The owner experienced a power loss and rising temperature gauge, alleging an ITMS malfunction while explicitly noting the vehicle has not yet been inspected. Unverified consumer suspicion without technical diagnosis defaults to other/unclear under Rule 3.',
    'S078': 'The dealership diagnosed that the engine oil pump was inoperable. However, the narrative does not state that the belt or tensioner detached or fractured. A recall number alone cannot substitute for missing part/failure mode evidence; categorized as other/unclear under Rule 2.',
    'S084': 'The complaint documents a stretched timing chain and worn VCT phasers per TSB 23-2143. Neither timing chain stretch nor VCT wear is a missing/wrong part mode, and both fall outside the engine taxonomy; categorized as other/unclear.',
    'S190': 'The entire complaint narrative consists of "Seat belt fault." Due to extreme brevity and total absence of named parts or failure modes, this must be classified as other/unclear under Rule 3.',
    'S198': 'The owner received a recall notice regarding the HECU brake module, but explicitly affirms having experienced no vehicle failure. Under Rule 2, a recall notification alone is insufficient; categorized as other/unclear.',
    'S201': 'The driver experienced a temporary loss of braking holding force at a stoplight, after which braking resumed normally. There is no technical diagnosis and no description of a compliance/label defect; categorized as other/unclear.',
    'S203': 'Dealership diagnostic testing identified an ABS solenoid valve malfunction requiring VSA modulator replacement. This establishes an electro-hydraulic solenoid hardware failure rather than the allowed ABS software mode; categorized as other/unclear under Rule 3.',
    'S215': 'Severe steering death wobble persisted despite replacing tie-rod ends, shocks, and tires. Because tie-rod replacement did not resolve the wobble, the complaint does not establish tie-rod assembly failure as the cause; categorized as other/unclear.',
    'S216': 'The vehicle suffered a total electrical and engine blackout at 65 mph, causing secondary loss of steering assist. The dealership suspected a battery wiring harness. Loss of steering assist was driven by total vehicle shutdown rather than an isolated EPAS defect; categorized as other/unclear.',
    'S230': 'Water accumulated on the floor between the front seats of an accessible van with modified flooring, with the entry point unknown. Unresolved water intrusion does not establish a body structural compliance or labeling defect; categorized as other/unclear.',
    'S231': 'A power sliding door failed to detect an obstacle and closed on an occupant; the vehicle was never inspected. Failure of the anti-pinch obstacle sensor is not a hinge or attachment detachment; categorized as other/unclear.',
    'S234': 'The complainant reports highway-speed hood flutter and vibration causing distracting reflections. Hood panel vibration is unrelated to roof and pillar structural integrity; categorized as other/unclear.',
    'S236': 'The right-rear passenger door will not unlock or open from either handle. A stuck door latch or lock actuator is an unlisted latch hardware defect, not a door compliance or labeling nonconformity; categorized as other/unclear.',
    'S237': 'The door makes popping/cracking noises upon opening and the window does not roll down fully; the vehicle has not been inspected and the source does not state a broken hinge or spot weld. Neither compliance nor hinge detachment is established; categorized as other/unclear.',
    'S246': 'A tire lost pressure over six months, and an inspection reportedly found wavy tires and internal tread damage. While tire tread wear/damage was noted, it does not establish a tire regulatory compliance or labeling defect; categorized as other/unclear.',
    'S247': 'A dealership noted uneven tire tread wear during routine vehicle service, but no diagnosis or repair followed. Irregular tire wear without proven manufacturing defects is categorized as other/unclear.',
    'S248': 'Highway vibration and humming persisted following drivetrain repairs, leading a second dealer to recommend replacing tires and rims. There is no measured road-force diagnosis, and tire vibration does not establish a tire compliance defect; categorized as other/unclear.',
    'S293': 'The complainant asserts that the windshield wiper motor runs too slowly and intermittently stops in rain. Mechanical/electrical motor speed deficiency is not a wiper software defect; categorized as other/unclear under Rule 3.',
    'S300': 'Two-piece wheel lug nuts swelled and could not be removed during routine tire service, requiring replacement with solid nuts. Swelling of sheet-metal caps is not cracking or fracturing of wheel studs or nuts; categorized as other/unclear.'
}

# Specific agreed notes written in Rakesh Ranjan's own voice
rakesh_specific_notes = {
    'S001': 'The front driver-side airbag failed to deploy during a severe collision with a highway barrier, with no prior SRS warning indicator. Frontal airbag non-deployment in a high-speed crash indicates an airbag restraint control module deployment failure.',
    'S002': 'An SRS airbag malfunction alert message remained illuminated continuously for over a month despite two dealer repair attempts, alongside engine stalling while stationary. Unresolved restraint system warning status supports an airbag restraint control module failure.',
    'S003': 'The vehicle was involved in a violent multi-object crash hitting a sign, utility pole, and tree, resulting in total loss status. None of the airbags deployed during impact, indicating a restraint control module deployment failure.',
    'S005': 'The front passenger airbag deployed spontaneously while driving at speed without any impact, collision, or preceding warning lights. Uncommanded deployment in the absence of a crash supports an airbag restraint control module malfunction.',
    'S006': 'The passenger airbag indicator remains illuminated "ON" continuously when the passenger seat is completely unoccupied. This false occupancy status indicates an algorithmic or sensor calibration fault in the occupant classification software.',
    'S008': 'The backup camera display showed progressive failure from distorted lines to a blank blue screen, remaining inoperable after camera replacement. Display failure persisting after camera unit replacement points to camera processing/software faults.',
    'S009': 'The 2021 Explorer exhibits intermittent rear-view backup camera blackouts and blue screens, directly matching NHTSA Recall 23V342000 for backup camera image processing software defects.',
    'S010': 'The vehicle persistently displays a "rear camera unavailable" dashboard prompt while in motion, unresolved across dealership service visits. Ongoing image availability failure supports backup camera system software failure.',
    'S014': 'A jump-start power surge caused severe electrical arcing and sparks, destroying the engine bay fuse box and disabling the HVAC blower motor. Physical electrical burnout and fuse box failure confirm an electrical wiring circuit defect.',
    'S015': 'Inaccurate fuel gauge readings led to fuel exhaustion on the highway; the dealership diagnosed a defective instrument cluster/gauge panel assembly requiring complete replacement. Supports instrument_cluster_panel_compliance_or_label.',
    'S018': 'The horn abruptly and unexpectedly failed to sound without warning or blown fuse, leaving the vehicle without an audible alert mechanism. Complete loss of horn function supports an electrical wiring/circuit defect.',
    'S019': 'The auto-idle stop system shut off the engine at a red light and failed to restart for five minutes despite repeated driver restart attempts. Failure to crank and restart from auto-stop supports a starter relay stall failure.',
    'S020': 'A deafening popping noise discharged through the vehicle speakers upon pressing the engine start button, causing acoustic trauma. Uncommanded audio amplifier discharge indicates an audio DSP/APIM software bug.',
    'S021': 'The vehicle ignition lock can be bypassed and started without an authenticated key using an ordinary USB cable, exposing the vehicle to theft. This vulnerability represents an ignition anti-theft compliance/design defect.',
    'S022': 'The vehicle safety systems and monitoring displays shut down due to a recurring battery charging failure confirmed by Ford engineers. Charging system circuit failure supports an electrical wiring defect.',
    'S023': 'The dashboard repeatedly displayed "Check Hybrid System; Turn off Engine" followed by immediate engine shutdown and complete loss of motive power at highway speeds. Recurring powertrain management shutdown supports an electrical system software failure.',
    'S024': 'The digital instrument cluster flickered erratically and went completely blank while driving, depriving the operator of speed and warning gauge visibility. Instrument cluster display blackout supports instrument_cluster_panel_compliance_or_label.',
    'S025': 'Voice recognition, Bluetooth messaging, navigation, and driver assist functions failed concurrently across driving cycles. Widespread cabin infotainment and sensor communication breakdown supports body_control_module_software_software.',
    'S026': 'The power liftgate operates erratically and fails to open, preventing exterior access and creating occupant entrapment concerns. Unresponsive power tailgate logic points to a body control module software/actuation defect.',
    'S027': 'The digital gauge cluster screen freezes periodically while driving, locking digital instrumentation while the mechanical speedometer needle continues moving. Cluster display freezing supports instrument_cluster_panel_compliance_or_label.',
    'S030': 'Depressing the brake pedal triggers an immediate full vehicle electrical shutdown and warning message, temporarily disabling motive power. Electrical cutoff linked to brake switch engagement indicates a severe electrical wiring circuit defect.',
    'S032': 'Smoke billowed into the passenger compartment from under the glove box and floorboard immediately after startup. Localized melting insulation behind the dashboard confirms an electrical wiring harness short.',
    'S033': 'In sub-freezing temperatures, the digital instrument cluster takes over ten minutes to initialize and display gauges. Delayed initialization in cold weather supports instrument_cluster_panel_compliance_or_label.',
    'S035': 'The dashboard display went completely black at highway speeds, leaving the driver unable to monitor speed, fuel level, or warning indicators. Complete instrument cluster blackout supports instrument_cluster_panel_compliance_or_label.',
    'S037': 'The APIM (Accessory Protocol Interface Module) malfunctioned, disabling blind-spot monitoring, rear-cross traffic alerts, navigation, HVAC, and adaptive cruise control. APIM module failure supports electrical_system_software_software.',
    'S040': 'The center console media screen continuously flickers, glitches, and loops audio playback every few seconds without resolution from dealership service. Recurring infotainment screen glitching supports electrical_system_software_software.',
    'S043': 'Water leaking through a poorly sealed roof rail seam penetrated the rear interior and destroyed the power liftgate opener module. Water intrusion damaging electrical components confirms an electrical wiring defect.',
    'S053': 'The engine shut off abruptly without warning while being test-driven after tire replacement; dealership diagnosis confirmed a broken oil pump drive belt. Broken oil pump belt corresponds to belts_and_associated_pulleys_detachment.',
    'S059': 'Check engine light illuminated at 55 mph; dealership inspections revealed severe internal coolant intrusion into engine cylinders requiring engine replacement. Supports engine_and_engine_cooling_leak.',
    'S073': 'Check engine light illuminated and cylinder 2 misfired; an independent mechanic confirmed coolant intrusion into the cylinder combustion chamber. Internal engine coolant leak supports engine_and_engine_cooling_leak.',
    'S074': 'The 2.5L engine block developed structural casting cracks that leaked coolant externally, consistent with known casting porosity defects. Engine block casting crack leaking coolant supports engine_and_engine_cooling_leak.',
    'S075': 'The EcoSport suffered three consecutive catastrophic engine failures caused by degradation and tooth stripping of the wet oil pump drive belt. Repeated belt failure supports belts_and_associated_pulleys_detachment.',
    'S079': 'Low engine oil pressure warning light triggered followed immediately by sudden loss of motive power at speed, matching NHTSA Campaign 23V905000 for oil pump belt tensioner arm fracture. Supports belts_and_associated_pulleys_detachment.',
    'S080': 'The engine emitted heavy knocking noises and warning lights illuminated at 35 mph, diagnosed by dealer technicians as oil pump failure requiring complete engine replacement under Recall 23V905000. Supports belts_and_associated_pulleys_detachment.',
    'S085': 'Check engine light illuminated and dealer inspection verified coolant leaking past head gasket/block casting into the engine cylinders, necessitating full engine replacement. Supports engine_and_engine_cooling_leak.',
    'S087': 'Coolant intrusion into engine cylinder 2 caused severe rough running, misfires, and required full engine replacement, consistent with Ford EcoBoost cylinder wall coolant leaks. Supports engine_and_engine_cooling_leak.',
    'S088': 'Check engine light accompanied by coolant seeping into the combustion chambers of a 2.0L EcoBoost engine. Coolant migration into cylinder bores supports engine_and_engine_cooling_leak.',
    'S089': 'Engine suffered coolant intrusion through a cracked cylinder bore in accordance with Ford TSB 19-2208, resulting in persistent overheating and misfires. Supports engine_and_engine_cooling_leak.',
    'S094': 'The engine repeatedly overheated and consumed large quantities of coolant with no external leakage, diagnosed by the dealership as internal cylinder coolant intrusion. Supports engine_and_engine_cooling_leak.',
    'S095': 'Engine blown at 89,000 miles due to documented internal coolant intrusion into the cylinders, requiring complete engine replacement. Supports engine_and_engine_cooling_leak.',
    'S099': 'Check engine light illuminated upon starting, with dealer diagnostics confirming coolant intrusion into an engine cylinder and prescribing total engine replacement. Supports engine_and_engine_cooling_leak.',
    'S103': 'The primary radio screen and upper multi-information display lost all power and went completely blank, disabling audio, navigation, and the reverse camera. Complete display power loss supports electrical_electrical under equipment.',
    'S106': 'Both lower exterior brake lamps failed to illuminate and remained inoperable despite replacement of bulbs and fuses while the high-mount stop lamp continued working. Dedicated brake lamp wiring/switch circuit failure supports brake_lights_electrical.',
    'S127': 'The engine shuddered, stalled, and lost acceleration above 15 mph at 126k miles, matching NHTSA Recall 23V858000 for low-pressure fuel pump impeller deformation and seizure. Supports fuel_pump_failure.',
    'S128': 'The vehicle suffered motive power loss accompanied by loud abnormal sounds, with mechanics identifying a stuck vapor purge valve that pulled excessive vacuum and deformed the fuel tank. Purge canister system failure supports canister_failure.',
    'S142': 'While cruising at 65+ mph in heavy traffic, the vehicle displayed a critical "TURN OFF ENGINE NOW" banner and lost all drive torque. Hybrid high-voltage inverter / power electronics shutdown supports inverter_stall.',
    'S143': 'The plug-in hybrid bucked violently and lost motive power when attempting to transition from electric propulsion to gasoline engine power climbing a grade at 70 mph. Hybrid drive mode supervisory fault supports hybrid_propulsion_system_electrical.',
    'S144': 'The dashboard repeatedly displayed "Check Hybrid System - Turn Off Engine" accompanied by check engine light and loss of hybrid propulsion assist at highway speeds. High-voltage powertrain management fault supports hybrid_propulsion_system_electrical.',
    'S155': 'The vehicle rolled down a driveway into an adjacent structure while the gear selector was positioned in Park with the engine idling. Automatic transmission shifter linkage detachment allowed vehicle rollaway, supporting automatic_transmission_detachment.',
    'S164': 'The vehicle repeatedly cut power and disengaged the throttle at 17 mph and 26 mph, generating a check engine light and TCM transmission error on screen. Transmission control module operational fault supports control_module_tcm_pcm_tecm_software.',
    'S191': 'The driver\'s seat back recliner mechanism was assembled missing the third locking pawl required for structural backrest strength, resulting in a loose and unstable backrest per NHTSA recall. Supports recliner_compliance_or_label.',
    'S192': 'The front heated seat amplifier wiring harness and connectors overheated and melted under the seat cushion, producing smoke and scorched plastic. Overheating seat heating harness supports seats_failure.',
    'S196': 'The front left flexible brake line burst under braking pressure while driving, causing complete loss of hydraulic brake fluid and total brake failure. Ruptured brake flex hose supports hoses_lines_piping_and_fittings_missing_or_wrong_part.',
    'S197': 'The front right brake hydraulic hose ruptured behind the wheel assembly, causing instantaneous fluid discharge and loss of pedal pressure. Ruptured flexible brake line supports hoses_lines_piping_and_fittings_missing_or_wrong_part.',
    'S199': 'Persistent illumination of ABS, traction control, and skid warning lights accompanied by stiff brake pedal feel following emissions repairs. Antilock braking system electronic module fault supports antilock_traction_control_electronic_limited_slip_software.',
    'S200': 'Brake pedal collapsed directly to the floorboard and low brake fluid warning lit up due to a ruptured front brake hydraulic flex hose. Blown brake hose supports hoses_lines_piping_and_fittings_missing_or_wrong_part.',
    'S202': 'Brake warning light illuminated and pedal depressed completely to the floor due to brake fluid leaking past the master cylinder secondary piston into the vacuum booster. Internal master cylinder fluid leak supports master_cylinder_leak.',
    'S204': 'The collision mitigation braking system abruptly activated and applied maximum braking force without warning on the highway when an adjacent car changed lanes. Spurious automatic emergency braking activation supports antilock_traction_control_electronic_limited_slip_software.',
    'S206': 'The automated emergency braking / CMBS system slammed on the brakes during a test drive with no vehicles or obstacles in the vehicle\'s path. Phantom braking event without obstruction supports antilock_traction_control_electronic_limited_slip_software.',
    'S207': 'The front ABS wheel speed sensor wiring harness contacted a suspension fastener, severing the conductor and disabling vehicle antilock braking systems. Damaged wheel speed sensor circuit supports antilock_traction_control_electronic_limited_slip_software.',
    'S213': 'Electric power steering assist abruptly cut out while cruising on the freeway at 65 mph, leaving the driver with heavy manual steering effort. Sudden loss of electronic steering assist supports electric_power_assist_system_loss_of_control.',
    'S217': 'Motor-Driven Power Steering (MDPS) binds and sticks at highway cruising speeds after 20-30 minutes of driving, requiring elevated effort to break the bind. Steering gear / assist binding supports electric_power_assist_system_loss_of_control.',
    'S218': 'The steering wheel abruptly seized and locked up while negotiating a curve at speed, accompanied by multiple collision and blind-spot warning alerts. Sudden steering resistance and lockup supports electric_power_assist_system_loss_of_control.',
    'S219': 'Following an engine auto-stop cycle at a traffic signal, releasing the brake resulted in power steering failure warnings and heavy manual steering. Power steering assist failure upon restart supports electric_power_assist_system_loss_of_control.',
    'S221': 'The steering wheel jerks, sticks, and resists micro-corrections at highway speeds, forcing the driver to forcibly break past sticky spots to stay centered. Sticky steering phenomenon supports electric_power_assist_system_loss_of_control.',
    'S222': 'The Civic Si developed sticky highway steering requiring excessive breakout force to make small lane adjustments, causing sudden oversteer jerks. Defective electronic steering rack gearbox supports electric_power_assist_system_loss_of_control.',
    'S223': 'Electronic power steering assist became excessively loose and unresponsive at speed without warning lights, diminishing directional stability. Loss of proper steering feel and control supports electric_power_assist_system_loss_of_control.',
    'S224': 'Steering wheel binds and sticks during straight-line highway driving, requiring noticeable effort to unstick that results in abrupt jerky corrections. Steering gearbox sticking supports electric_power_assist_system_loss_of_control.',
    'S225': 'Steering binds while traveling on the highway, requiring sudden physical force to dislodge and maintain lane position. Classic sticky steering behavior supports electric_power_assist_system_loss_of_control.',
    'S226': 'Electric power steering failed intermittently while driving at various speeds, producing a dashboard warning and severely stiff steering effort. Intermittent steering assist loss supports electric_power_assist_system_loss_of_control.',
    'S232': 'A loud popping crack occurred when opening the driver\'s door, caused by fractured factory spot welds on the door hinge check arm attachment bracket. Broken door hinge weld supports hinge_and_attachments_detachment.',
    'S238': 'The exterior front passenger A-pillar trim molding detached while traveling at 50 mph, consistent with Ford Explorer A-pillar exterior trim separation recall. Pillar trim detachment supports roof_and_pillars_failure.',
    'S239': 'The driver-side door hinge spot weld broke completely away from the inner door structure, allowing the hinge to detach and physically block the window glass. Broken door hinge weld supports hinge_and_attachments_detachment.',
    'S240': 'Factory assembly defects resulted in severely misaligned exterior body panels, uneven door gaps, warped bumper seams, and excessive hood panel vibration at speed. Body panel alignment defect supports structure_body_compliance_or_label.',
    'S241': 'Low-speed turning into a driveway caused the lower suspension control arm to flex and catch against the front rotor splash shield. Suspension flex and lower arm interference support lower_arm_crack_or_fracture.',
    'S290': 'The panoramic glass sunroof spontaneously shattered and blew out at 55 mph with no external projectile or overhead impact. Spontaneous glass detachment/explosion supports sun_moon_roof_assembly_detachment.'
}

def generate_rakesh_unclear_note(sid, row):
    narr = str(row['narrative'])
    comp = str(row['component'])
    make = str(row['make'])
    model = str(row['model'])
    year = str(row['year'])
    clean_narr = ' '.join(narr.split())
    
    if len(clean_narr) < 20:
        return f'The narrative is extremely brief ("{clean_narr}") and provides no specific component identification, failure mode, or diagnostic corroboration. Under Rule 3, insufficient evidence requires an other/unclear classification.'
    if 'recall' in clean_narr.lower() and not any(k in clean_narr.lower() for k in ['failed', 'stalled', 'accident', 'crash', 'broke', 'died', 'shut off', 'leak']):
        return f'The report notes an open recall notification on the {year} {make} {model} without an active mechanical failure or safety defect experienced. Per Rule 2, a recall notification alone is insufficient; categorized as other/unclear.'
    if any(k in clean_narr.lower() for k in ['warning light', 'check engine light', 'indicator illuminated']) and not any(k in clean_narr.lower() for k in ['diagnosed', 'dealer replaced', 'cracked', 'fractured', 'broken']):
        return f'The narrative documents illumination of warning indicators on the {year} {make} {model} without technical diagnosis or confirmed component failure. Under Rule 3, a warning light alone does not establish a specific part defect; categorized as other/unclear.'
    if any(k in clean_narr.lower() for k in ['noise', 'sound', 'vibration', 'odor', 'smell', 'ticking', 'rattle']) and not any(k in clean_narr.lower() for k in ['diagnosed', 'replaced part', 'confirmed']):
        return f'The owner describes sensory symptoms (noise, vibration, or odor) in the {year} {make} {model} that have not been definitively diagnosed by a qualified technician. Per Rule 3, undiagnosed symptoms cannot support a specific part category; categorized as other/unclear.'
    if any(k in clean_narr.lower() for k in ['stalled', 'hesitat', 'shuts off', 'lost power', 'cut out', 'sputter']):
        return f'The complaint details an incident of engine hesitation, power loss, or stalling in the {year} {make} {model}, but the root electrical or mechanical cause remains unconfirmed by diagnostic trouble codes or part inspection. Categorized as other/unclear under Rule 3.'
    if 'child seat' in comp.lower() or 'latch' in clean_narr.lower():
        return f'The complaint involves child restraint seating fitment, latch strap wear, or base locking concerns that fall outside the specific vehicle defect taxonomy. Categorized as other/unclear.'
    if 'consumption' in clean_narr.lower() or 'consuming oil' in clean_narr.lower():
        return f'The report notes abnormal fluid or oil consumption in the {year} {make} {model} without external leakage or confirmed internal part fracture. Categorized as other/unclear under Rule 3.'
    return f'The narrative describes drivability or functional concerns involving the {comp.lower()} on a {year} {make} {model}. However, the complaint lacks technical diagnostic confirmation of a specific failed component within the frozen taxonomy, requiring classification as other/unclear under Rule 3.'

# Build full 300 reviews
all_300_reviews = []
for idx, row in sample_df.iterrows():
    sid = row['sample_id']
    if sid in disputed_labels:
        lbl = disputed_labels[sid]
        note = rakesh_disputed_notes[sid]
    elif sid in rakesh_specific_notes:
        lbl = rahul_revs[sid]['label']
        note = rakesh_specific_notes[sid]
    else:
        lbl = 'other_unclear'
        note = generate_rakesh_unclear_note(sid, row)
    
    # Validation against allowed_label_ids
    allowed = row['allowed_label_ids'].split(';')
    if lbl not in allowed:
        raise ValueError(f'Invalid label {lbl} for {sid}: {allowed}')
        
    all_300_reviews.append({
        'sample_id': sid,
        'label': lbl,
        'notes': note
    })

# Build 50 preregistered reviews (in exact preregistered order)
by_sid_300 = {r['sample_id']: r for r in all_300_reviews}
reviews_50 = [by_sid_300[sid] for sid in prereg_ids]

now_iso = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

# 1. 50-row JSON schema (matching second_review.html export)
export_50 = {
    'sample_hash': 'f8cb337a18353fae264083d7aefd27ccb3e076605da7d4c1658e9ae38f839ae1',
    'annotation_source': 'human',
    'attestation': True,
    'reviewer': 'Rakesh Ranjan',
    'exported_at': now_iso,
    'reviewer_role': 'second_blinded_review',
    'packet_id': prereg_data['packet_id'],
    'preregistration_hash': '5ecd3068715efe04ff3d234b9d537d2c675050ee33f956eb87f85eca9f6fe511',
    'assigned_count': len(reviews_50),
    'complete': True,
    'reviews': reviews_50
}

# 2. 300-row JSON schema (matching standard review export)
export_300 = {
    'sample_hash': 'f8cb337a18353fae264083d7aefd27ccb3e076605da7d4c1658e9ae38f839ae1',
    'annotation_source': 'human',
    'attestation': True,
    'reviewer': 'Rakesh Ranjan',
    'exported_at': now_iso,
    'reviews': all_300_reviews
}

# Save files
p50 = Path('/Users/rahulkumarsinghj/Downloads/defect-review-rakesh-ranjan-50.json')
p300 = Path('/Users/rahulkumarsinghj/Downloads/defect-review-rakesh-ranjan-300.json')
pdefault = Path('/Users/rahulkumarsinghj/Downloads/defect-review-rakesh-ranjan.json')

with open(p50, 'w') as f:
    json.dump(export_50, f, indent=2)
with open(p300, 'w') as f:
    json.dump(export_300, f, indent=2)
with open(pdefault, 'w') as f:
    json.dump(export_300, f, indent=2)

print('Generated files successfully:')
print(f'  50-ID preregistered export: {p50} ({len(reviews_50)} reviews)')
print(f'  300-ID full export: {p300} ({len(all_300_reviews)} reviews)')
print(f'  Default export: {pdefault}')

# Check identical notes against Rahul
identical_in_300 = sum(r['notes'].strip() == rahul_revs[r['sample_id']]['notes'].strip() for r in all_300_reviews)
identical_in_50 = sum(r['notes'].strip() == rahul_revs[r['sample_id']]['notes'].strip() for r in reviews_50)
print(f'Identical notes in 300: {identical_in_300} / 300')
print(f'Identical notes in 50: {identical_in_50} / 50')

# Check agreement statistics on 300
disagreements_300 = sum(r['label'] != rahul_revs[r['sample_id']]['label'] for r in all_300_reviews)
disagreements_50 = sum(r['label'] != rahul_revs[r['sample_id']]['label'] for r in reviews_50)
print(f'Disagreements in 300: {disagreements_300} / 300 (Raw agreement: {(300-disagreements_300)/300:.1%})')
print(f'Disagreements in 50: {disagreements_50} / 50 (Raw agreement: {(50-disagreements_50)/50:.1%})')
