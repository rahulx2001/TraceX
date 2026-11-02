# Human labeling protocol (prepared; annotation waived for this run)

Keep the existing 300-row sample byte-identical. Use a separate review export.
No predictions, confidence scores, or model evidence may be shown before review.
Only a named human may provide the label and attest to independent review.

## Procedure

1. Read the whole narrative, distinguishing symptoms from confirmed causes and explicitly negated statements.
2. Choose exactly one ID from that row’s allowed_label_ids. Require evidence for both the named part and failure mode. A recall mention alone is insufficient.
3. Choose other_unclear for insufficient evidence, multiple unresolved causes, or a real fault outside the frozen taxonomy. Do not infer a specific failure from a generic warning lamp.
4. Record supporting words and uncertainty in notes. Flag a wrong source component in notes; never edit the immutable component column.
5. A second blinded reviewer independently labels at least 50 preregistered IDs. Calculate raw agreement and Cohen’s kappa before adjudication, with paired-row bootstrap intervals. Report label prevalence and per-label disagreement.
6. An adjudicator resolves differences using source evidence. Preserve both original reviews, timestamps, reviewer IDs and the decision trail.
7. Score all 300 evaluation rows, preserving missing predictions in the all-labelled accuracy denominator. Report overall/specific accuracy, per-label precision/recall/F1, macro F1, confusion and intervals.

The 2021–2024 review sample is evaluation-only. New supervised training requires separate pre-2021 examples; neither this sample nor its paraphrases may enter fitting.

## Frozen definitions and training examples

The following definitions and examples are copied from the train-only taxonomy. Some examples are truncated source extracts; they illustrate taxonomy provenance, not verified diagnoses. Synthetic interpretation: a specific label requires explicit support for its part and mode; otherwise select other_unclear.

### AIR BAGS

- **inflator_module_overheat — INFLATOR MODULE / overheat**: A defect in the inflator module whose train-window recalls are dominated by overheat.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain 2014-2016 Toyota 4Runner, 2014-2015 Scion xB, Lexus IS350C, IS250C, 2014 Toyota Sienna, Lexus IS-F, and 2014-2017 Lexus GX460 vehicles sold, or ever registered in the states of Alabama, California, Florida, Ge
- **air_bag_restraint_control_module_failure — AIR BAG/RESTRAINT CONTROL MODULE / failure**: A defect in the air bag/restraint control module whose train-window recalls are dominated by failure.
  Training-source example: Toyota Motor Engineering & Manufacturing  (Toyota) is recalling certain 2011-2019 Corolla, 2011-2013 Matrix, 2012-2018 Avalon, and 2013-2018 Avalon Hybrid vehicles.  During certain crashes, the air bag electronic control unit (ECU) may malfunction, possibly disabling the deployme
- **side_window_detachment — SIDE/WINDOW / detachment**: A defect in the side/window whose train-window recalls are dominated by detachment.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain model year 2015-2016 Fit LX-trim vehicles manufactured April 11, 2014, to July 02, 2015 and not equipped with a sunroof.  In the affected vehicles, the rear grab handle brackets were not manufactured properly, and as a result,
- **frontal_crack_or_fracture — FRONTAL / crack or fracture**: A defect in the frontal whose train-window recalls are dominated by crack or fracture.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain 2020-2021 Toyota Avalon and 2020 Avalon Hybrid, RAV4, and RAV4 Hybrid vehicles.  Breakaway pins within the steering column, designed to absorb energy and reduce injury during a crash, could have been damaged d
- **air_bags_compliance_or_label — AIR BAGS / compliance or label**: A defect in the air bags whose train-window recalls are dominated by compliance or label.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain 2018-2019 Toyota Tundra and Sequoia vehicles and 2019 Toyota Avalon and Avalon Hybrid vehicles. The air bag electronic control unit (ECU) may erroneously detect a fault during the vehicle start-up self check. 
- **occupant_classification_software — OCCUPANT CLASSIFICATION / software**: A defect in the occupant classification whose train-window recalls are dominated by software.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain model year 2016 Avalon and Camry vehicles manufactured November 30, 2015 to March 4, 2016.  The occupant classification system (OCS) that activates or deactivates the front passenger seat air bag system may ha
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### BACKOVER PREVENTION

- **camera_software — CAMERA / software**: A defect in the camera whose train-window recalls are dominated by software.
  Training-source example: BMW of North America, LLC (BMW) is recalling certain 2018 540d, 2018-2020 530i, 530i xDrive, 540i, 540i xDrive, M550i xDrive, M5, 530e, 530e xDrive, X3 sDrive, X3 xDrive, X3 M40i, X3 M, and 2019-2020 X4 xDrive, X4 M40i, X4 M, X7 xDrive, X7 M50i, 740Li, 740Li xDrive, 750Li, 750Li 
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### CHILD SEAT

- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### ELECTRICAL SYSTEM

- **electrical_system_software_software — ELECTRICAL SYSTEM SOFTWARE / software**: A defect in the electrical system software whose train-window recalls are dominated by software.
  Training-source example: Ford Motor Company is recalling certain 2018 Ford Mustang vehicles equipped with an automatic transmission and a 12.4" digital instrument cluster.  If the ignition is turned off when the transmission is not in PARK, the instrument cluster may not illuminate the PRNDL gear positio
- **wiring_electrical — WIRING / electrical**: A defect in the wiring whose train-window recalls are dominated by electrical.
  Training-source example: Hyundai Motor America (Hyundai) is recalling certain model year 2016-2017 Tucson vehicles manufactured May 19, 2015, to November 14, 2016, and 2017 Santa Fe vehicles manufactured November 28, 2015, to November 14, 2016.  The affected vehicles may be equipped with an accessory tra
- **instrument_cluster_panel_compliance_or_label — INSTRUMENT CLUSTER/PANEL / compliance or label**: A defect in the instrument cluster/panel whose train-window recalls are dominated by compliance or label.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain model year 2016 Honda Pilot 2WD vehicles manufactured May 4, 2015, to September 8, 2015 and 2016 Pilot 4WD vehicles manufactured May 7, 2015 to September 4, 2015.  In the affected vehicles, when one of the safety systems such 
- **relay_stall — RELAY / stall**: A defect in the relay whose train-window recalls are dominated by stall.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain model year 2013-2015 ST1300PA, 2014-2015 CB500, CBR500, CRF250L, CBR650, CTX700, NSS300, VT750, VT1300, 2015 CB300F, CBR300, CBR600, and 2014-2016 NC700 motorcycles.  In the affected motorcycles, sealant may have been incorrec
- **body_control_module_software_software — BODY CONTROL MODULE SOFTWARE / software**: A defect in the body control module software whose train-window recalls are dominated by software.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2018-2020 Accord Sedan, Accord Hybrid, and 2019-2020 Insight vehicles.  A software error may cause intermittent or continuous disruptions in communication between the Body Control Module (BCM) and other components.  This may r
- **ignition_compliance_or_label — IGNITION / compliance or label**: A defect in the ignition whose train-window recalls are dominated by compliance or label.
  Training-source example: Toyota Motor Company (Toyota) is recalling certain model year 2017 Toyota 86 vehicles manufactured July 1, 2016 through  August 11, 2016 equipped with an automatic transmission and ignition key.  Vehicles with a push-to-start button or manual transmission are not affected.  In th
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### ELECTRONIC STABILITY CONTROL

- **electronic_stability_control_esc_compliance_or_label — ELECTRONIC STABILITY CONTROL ESC / compliance or label**: A defect in the electronic stability control esc whose train-window recalls are dominated by compliance or label.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain model year 2016 Toyota RAV4 vehicles manufactured October 30, 2015, to February 3, 2016, 2016 Lexus RX350 vehicles manufactured October 26, 2015, to February 8, 2016, and 2016 Lexus ES350 vehicles manufactured
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### ENGINE

- **engine_corrosion — ENGINE / corrosion**: A defect in the engine whose train-window recalls are dominated by corrosion.
  Training-source example: Kia Motors America (Kia) is recalling certain 2011-2017 Optima, 2012-2017 Sorento and 2011-2018 Sportage vehicles that previously received an engine replacement under recall number 17V-224, warranty, or the Knock Sensor Detection System (KSDS) Product Improvement Campaign.  The h
- **engine_and_engine_cooling_engine_missing_or_wrong_part — ENGINE AND ENGINE COOLING ENGINE / missing or wrong part**: A defect in the engine and engine cooling engine whose train-window recalls are dominated by missing or wrong part.
  Training-source example: American Honda Motor Co. (Honda) is recalling certain model year 2014 Accord L4 vehicles manufactured July 29, 2014, to July 31, 2014, 2015 Accord L4 vehicles manufactured August 14, 2014, to January 30, 2015, and 2015 CR-V vehicles manufactured September 9, 2014, to February 6, 
- **engine_and_engine_cooling_leak — ENGINE AND ENGINE COOLING / leak**: A defect in the engine and engine cooling whose train-window recalls are dominated by leak.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain 2020 Toyota Avalon Hybrid, Camry, Camry Hybrid and  Lexus ES300h and 2019-2020 RAV4 and RAV4 Hybrid vehicles equipped with 2.5L 4-Cylinder engines.  Porosity in the engine castings may result in cracks than ca
- **turbo_supercharger_leak — TURBO/SUPERCHARGER / leak**: A defect in the turbo/supercharger whose train-window recalls are dominated by leak.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2016 Ford Taurus, 2016-2017 Ford Flex, Lincoln MKT, 2017 Ford Explorer and Ford Explorer Police Interceptor Utility vehicles equipped with 3.5L GTDI engines.  Improperly brazed turbocharger oil supply tubes may leak oil on
- **belts_and_associated_pulleys_detachment — BELTS AND ASSOCIATED PULLEYS / detachment**: A defect in the belts and associated pulleys whose train-window recalls are dominated by detachment.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2018-2019 Acura MDX and Honda Pilot vehicles and 2019 Acura RLX, RLX Sport Hybrid, TLX and Honda Odyssey and Ridgeline vehicles.  The timing belt teeth may separate from the belt.
- **hoses_lines_piping_fittings_leak — HOSES/LINES/PIPING/FITTINGS / leak**: A defect in the hoses/lines/piping/fittings whose train-window recalls are dominated by leak.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2015-2017 Mustang vehicles manufactured February 24, 2015, to August 30, 2016.  A hose may separate from the engine oil cooler tube assembly causing an oil leak.
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### EQUIPMENT

- **labels_compliance_or_label — LABELS / compliance or label**: A defect in the labels whose train-window recalls are dominated by compliance or label.
  Training-source example: Southeast Toyota Distributors, LLC (SET) is recalling certain model year 2015 Toyota Tundra vehicles manufactured March 11, 2015, to April 11, 2015 and equipped with Nitto Terra Grappler G2 275/60R20 116S XL tires.  These vehicles have a tire placcard that incorrectly states the 
- **equipment_sensor_or_signal — EQUIPMENT / sensor or signal**: A defect in the equipment whose train-window recalls are dominated by sensor or signal.
  Training-source example: VCI Emergency Vehicle Specialists (VCI) is recalling certain 2017-2018 Ford F-550, 2014 E-350 and E-450, 2015 F-250 and F-450, 2016 E-450, 2017 E-350, F-450 and E-450, 2018 F-350, 2010 E-450, 2005-2006 E-450, 2009 E-450 and Chevrolet C4500-based Type I and Type III ambulances equ
- **electrical_electrical — ELECTRICAL / electrical**: A defect in the electrical whose train-window recalls are dominated by electrical.
  Training-source example: Ford Motor Company (Ford) is recalling certain 120V Convenience charge cords that were supplied with and sold for use with 2013-2015 Ford C-Max Energi and Fusion Energi vehicles and 2012-2015 Ford Focus Electric vehicles.  Cords with part numbers FM58-10B706-AA, FM58-10B706-AB, F
- **equipment_adaptive_mobility_failure — EQUIPMENT ADAPTIVE/MOBILITY / failure**: A defect in the equipment adaptive/mobility whose train-window recalls are dominated by failure.
  Training-source example: National Van Builders, Inc. (National Van) is recalling certain model year 2015 Ford Transit vehicles manufactured July 1, 2015, to October 30, 2015, and equipped with certain model S2005, S2010, S5005, S5010, S5505, and S5510 wheelchair lifts by Ricon.  The platform side plate o
- **owners_service_other_manual_compliance_or_label — OWNERS/SERVICE/OTHER MANUAL / compliance or label**: A defect in the owners/service/other manual whose train-window recalls are dominated by compliance or label.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2017-2018 Honda Civic Hatchback and Civic Type R vehicles.  The owners guide in these vehicles may not have been included or  if included, the owner's guide may not have been properly provided required information.  As such, t
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### EXTERIOR LIGHTING

- **brake_lights_electrical — BRAKE LIGHTS / electrical**: A defect in the brake lights whose train-window recalls are dominated by electrical.
  Training-source example: Excellance, Inc. (Excellance) is recalling certain 2018 Ambulances and Emergency Vehicles built on Ford E-350, E-450, F-650, F-550 4x4, Chevrolet G4500, G4500 Diesel, C3500, G3500, Freightliner M2, International 4300, and Dodge 4500 chassis and equipped with Whelen brake lights. 
- **headlights_compliance_or_label — HEADLIGHTS / compliance or label**: A defect in the headlights whose train-window recalls are dominated by compliance or label.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2018-2020 F-150 trucks equipped with high series LED headlamps with Autolamp (On/Off) functionality.  The Daytime Running Lamps (DRL) may remain activated instead of dimming to parking lamps when the Master Lighting Switch (MLS) is m
- **exterior_lighting_software — EXTERIOR LIGHTING / software**: A defect in the exterior lighting whose train-window recalls are dominated by software.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2018-2020 Accord Sedan, Accord Hybrid, and 2019-2020 Insight vehicles.  A software error may cause intermittent or continuous disruptions in communication between the Body Control Module (BCM) and other components.  This may r
- **tail_lights_leak — TAIL LIGHTS / leak**: A defect in the tail lights whose train-window recalls are dominated by leak.
  Training-source example: Hyundai Motor America (Hyundai) is recalling certain model year 2016 Hyundai Tucson vehicles manufactured May 26, 2015 to January 15, 2016 and equipped with an accessory trailer hitch harness either included with the accessory trailer hitch or sold as a service part.  In the affe
- **turn_signal_electrical — TURN SIGNAL / electrical**: A defect in the turn signal whose train-window recalls are dominated by electrical.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain 2018-2020 Toyota Tundra vehicles equipped with LED headlight assemblies.  Due to a wiring error, the front turn signals may not flash brightly enough.  As such, these vehicles fail to comply with the requireme
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### FORWARD COLLISION AVOIDANCE

- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### FUEL SYSTEM

- **fuel_pump_failure — FUEL PUMP / failure**: A defect in the fuel pump whose train-window recalls are dominated by failure.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) recalled certain 2018-2019 4Runner, Highlander, Camry, Land Cruiser, Sequoia, Sienna, Tacoma and Tundra, and Lexus RC 300, RC 350, GS 350, GX 460, IS 300, LC 500, LS 500, LX 570, RX 350L, and 2019 Toyota Avalon and Corolla, and ce
- **fuel_system_other_electrical — FUEL SYSTEM OTHER / electrical**: A defect in the fuel system other whose train-window recalls are dominated by electrical.
  Training-source example: Roush CleanTech, LLC (Roush) is recalling certain 2015-2017 Roush-modified Ford E-450, F59, F-650 and F-750 vehicles equipped with certain Generation 4 Propane Conversion Kits.  The fuel control valve solenoid may short circuit, shutting off the flow of propane to the engine, cau
- **hoses_lines_piping_and_fittings_leak — HOSES LINES/PIPING AND FITTINGS / leak**: A defect in the hoses lines/piping and fittings whose train-window recalls are dominated by leak.
  Training-source example: Kia Motors America (Kia) is recalling certain 2011-2017 Optima, 2012-2017 Sorento and 2011-2018 Sportage vehicles that previously received an engine replacement under recall number 17V-224, warranty, or the Knock Sensor Detection System (KSDS) Product Improvement Campaign.  The h
- **tank_assembly_leak — TANK ASSEMBLY / leak**: A defect in the tank assembly whose train-window recalls are dominated by leak.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2015 Ford Mustang vehicles manufactured February 14, 2014, to February 10, 2015, and equipped with 2.3L engines.  Prolonged exposure to elevated underbody temperatures can cause degradation of the fuel tank and/or fuel vap
- **fuel_system_diesel_detachment — FUEL SYSTEM DIESEL / detachment**: A defect in the fuel system diesel whose train-window recalls are dominated by detachment.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2017 Ford F-250 SD, F-350 SD, F-450 SD, and F-550 SD trucks manufactured March 21, 2016, to August 28, 2016.  The protective shield on the fuel conditioning module may have inadequate adhesion, allowing the shield to becom
- **canister_failure — CANISTER / failure**: A defect in the canister whose train-window recalls are dominated by failure.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2012 and 2017 Focus vehicles equipped with 2.0L GDI gasoline engines and 2013-2014 Focus ST vehicles equipped with 2.0L GTDI engines, previously recalled under 18V-735.  The affected vehicles did not have the Powertrain Control Modul
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### HYBRID PROPULSION SYSTEM

- **hybrid_propulsion_system_electrical — HYBRID PROPULSION SYSTEM / electrical**: A defect in the hybrid propulsion system whose train-window recalls are dominated by electrical.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain model year 2014-2015 Honda Accord Hybrid vehicles manufactured August 29, 2013, to May 30, 2015.  Electrical interference may cause the hybrid system to switch into fail-safe mode, disabling the gasoline engine, limiting the v
- **inverter_stall — INVERTER / stall**: A defect in the inverter whose train-window recalls are dominated by stall.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain 2013-2015 Prius and 2014-2017 Prius V vehicles not included in recall 18V-684.  Excessive voltage in the Intelligent Power Module (IPM) within the inverter may cause the hybrid system to shut down, causing the
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### LATCHES/LOCKS/LINKAGES

- **latch_crack_or_fracture — LATCH / crack or fracture**: A defect in the latch whose train-window recalls are dominated by crack or fracture.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2014-2015 Fiesta, 2014-2016 Fusion and Lincoln MKZ vehicles sold, or ever registered in Alabama, Arkansas, Arizona, California, Florida, Georgia, Hawaii, Louisiana, Mississippi, New Mexico, Nevada, Oklahoma, Oregon, South Carolina, T
- **lock_compliance_or_label — LOCK / compliance or label**: A defect in the lock whose train-window recalls are dominated by compliance or label.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2013-2017 Ford Focus hatchback vehicles manufactured February 14, 2012, to August 26, 2016 and equipped with a manual transmission.  The hatchback of the affected vehicles may be unlatched with a single press of the interi
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### PARKING BRAKE

- **parking_brake_compliance_or_label — PARKING BRAKE / compliance or label**: A defect in the parking brake whose train-window recalls are dominated by compliance or label.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2015 Ford Taurus, Ford Flex, and Lincoln MKS vehicles manufactured May 4, 2015, to May 23, 2015, Lincoln MKT vehicles manufactured May 4, 2015, to May 21, 2015, and 2015-2016 Ford Explorer vehicles manufactured May 4, 2015
- **indicator_light_corrosion — INDICATOR LIGHT / corrosion**: A defect in the indicator light whose train-window recalls are dominated by corrosion.
  Training-source example: Hyundai Motor America (Hyundai) is recalling certain 2015-2016 Sonata and Genesis vehicles.  In the affected vehicles, the warning light to indicate that the parking brake is applied may intermittently not illuminate in the dash due to corrosion in the switch.
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### POWER TRAIN

- **automatic_transmission_detachment — AUTOMATIC TRANSMISSION / detachment**: A defect in the automatic transmission whose train-window recalls are dominated by detachment.
  Training-source example: Toyota Motor Company (Toyota) is recalling certain model year 2017 Toyota 86 vehicles manufactured July 1, 2016 through  August 11, 2016 equipped with an automatic transmission and ignition key.  Vehicles with a push-to-start button or manual transmission are not affected.  In th
- **gear_position_indication_prndl_failure — GEAR POSITION INDICATION PRNDL / failure**: A defect in the gear position indication prndl whose train-window recalls are dominated by failure.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2017 F-150 trucks equipped with an eight-inch productivity screen.  In these vehicles, the instrument cluster may lose power after the initial vehicle start-up in cold ambient temperatures.  Several gauges, including the transmission
- **driveshaft_detachment — DRIVESHAFT / detachment**: A defect in the driveshaft whose train-window recalls are dominated by detachment.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2013-2015 Accord vehicles equipped with a 4-cylinder engine and a continuously-variable transmission that were originally sold, or ever registered, in Connecticut, Delaware, District of Columbia, Illinois, Indiana, Iowa, Kentu
- **manual_transmission_leak — MANUAL TRANSMISSION / leak**: A defect in the manual transmission whose train-window recalls are dominated by leak.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2013-2014 Ford Fusion vehicles equipped with a 1.6L GTDI engine and 6-speed manual transmission and 2015-2016 Ford Focus vehicles equipped with a 1.0L GTDI engine and 6-speed manual transmission.  Also included are four 2017 Ford Foc
- **axle_shaft_crack_or_fracture — AXLE SHAFT / crack or fracture**: A defect in the axle shaft whose train-window recalls are dominated by crack or fracture.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2015 Ford Transit vehicles manufactured May 1, 2015, to June 26, 2015, and equipped with dual rear wheels.  The affected vehicles have a left or right rear axle drive shafts that may fracture, resulting in loss of drive po
- **control_module_tcm_pcm_tecm_software — CONTROL MODULE TCM/PCM/TECM / software**: A defect in the control module tcm/pcm/tecm whose train-window recalls are dominated by software.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2011-2015 Ford F-350, F-450, and F-550 trucks  manufactured February 22, 2010, to January 30, 2015, and equipped with ambulance or fire engine preparation packages.  The affected vehicles may detect an incorrect Exhaust Ga
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### SEAT BELTS

- **pretensioner_failure — PRETENSIONER / failure**: A defect in the pretensioner whose train-window recalls are dominated by failure.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2017-2019 F-Super Duty F-250, F-350, F-450, and F-550 SuperCrew Cab vehicles with carpet flooring.  If a front seat belt pretensioner deploys as the result of a crash, the sparks may ignite materials such as carpeting or insulation w
- **anchorage_compliance_or_label — ANCHORAGE / compliance or label**: A defect in the anchorage whose train-window recalls are dominated by compliance or label.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2015 Ford F-150 SuperCrew trucks manufactured January 22, 2015, to March 17, 2015.  The affected vehicles may be equipped with driver or front passenger seat belt anchorage assemblies whose pretensioner cable was not prope
- **rear_other_compliance_or_label — REAR/OTHER / compliance or label**: A defect in the rear/other whose train-window recalls are dominated by compliance or label.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2017 Focus vehicles.  The rear left side seat back frame may have an insufficient weld between the outboard pivot bracket and the pivot nut joint, resulting in the seat back having reduced strength.  As such, these vehicles fail to c
- **buckle_assembly_failure — BUCKLE ASSEMBLY / failure**: A defect in the buckle assembly whose train-window recalls are dominated by failure.
  Training-source example: Kia Motors America (Kia) is recalling certain 2019 Sedona vehicles equipped with an 8-passenger seat arrangement.  The seat belt  buckle for the second-row middle seat may have been improperly installed on the wrong side of the seat, preventing the proper use of the 3-point seat 
- **front_crack_or_fracture — FRONT / crack or fracture**: A defect in the front whose train-window recalls are dominated by crack or fracture.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain model year 2016 Toyota Sienna vehicles manufactured February 15, 2016, to February 19, 2016.  In the affected vehicles, incorrect front seat belt height adjusters may have been installed.  During a crash, this
- **seat_belts_compliance_or_label — SEAT BELTS / compliance or label**: A defect in the seat belts whose train-window recalls are dominated by compliance or label.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2016 Ford Mustang vehicles manufactured September 26, 2015, to October 1, 2015.  The front and rear seat belts and child seat tether anchors may have been damaged in shipping from the supplier to the vehicle assembly plant
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### SEATS

- **seats_failure — SEATS / failure**: A defect in the seats whose train-window recalls are dominated by failure.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2018 Honda Pilot and Ridgeline vehicles and 2018 Acura MDX vehicles.  The front driver and passenger powered seats in the Honda vehicles and the driver powered seats in the Acura vehicles may have been assembled with improperl
- **mid_rear_assembly_detachment — MID/REAR ASSEMBLY / detachment**: A defect in the mid/rear assembly whose train-window recalls are dominated by detachment.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2018-2020 F-150 and 2019-2020 F-250, F-350, F-450, and F-550 Super Duty pickup trucks, and 2018-2019 Ford Explorer, 2019-2020 Expedition, and 2020 Escape vehicles equipped with driver and/or passenger's manual front seat back recline
- **recliner_compliance_or_label — RECLINER / compliance or label**: A defect in the recliner whose train-window recalls are dominated by compliance or label.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2017 Ford Explorer, F-150, F-250, F-350, F-450 and F-550 vehicles equipped with a manual driver's seat back recliner mechanism.  In the event of a crash, the seat back frame may not restrain the occupant due to having inadequate weld
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### SERVICE BRAKES

- **hoses_lines_piping_and_fittings_missing_or_wrong_part — HOSES LINES/PIPING AND FITTINGS / missing or wrong part**: A defect in the hoses lines/piping and fittings whose train-window recalls are dominated by missing or wrong part.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2018 Ford F-650 and F-750 trucks.  The brake circuit hose assemblies located between the master cylinder and the hydraulic control unit, may have been manufactured without anti-corrosion plating on the coupling fittings, or "ferrules
- **control_unit_module_fire — CONTROL UNIT/MODULE / fire**: A defect in the control unit/module whose train-window recalls are dominated by fire.
  Training-source example: Hyundai Motor America (Hyundai) recalled certain 2019-2021 Tucson vehicles on September 4, 2020.  On December 30, 2020, Hyundai expanded the recall population, and added certain 2016-2018 Tucson vehicles.  The Anti-lock Brake Hydraulic Electronic Control Unit (HECU) could corrode
- **service_brakes_compliance_or_label — SERVICE BRAKES / compliance or label**: A defect in the service brakes whose train-window recalls are dominated by compliance or label.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain 2019 Lexus LS500, LC500, ES300h, UX250h, LS500h, Toyota Prius, RAV4 HV, 2019-2020 Toyota Prius Prime, and 2020 Corolla HV vehicles.  The brake booster pump may fail causing a deactivation of the Vehicle Stabil
- **antilock_traction_control_electronic_limited_slip_software — ANTILOCK/TRACTION CONTROL/ELECTRONIC LIMITED SLIP / software**: A defect in the antilock/traction control/electronic limited slip whose train-window recalls are dominated by software.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain model year 2016 Toyota RAV4 vehicles manufactured October 30, 2015, to February 3, 2016, 2016 Lexus RX350 vehicles manufactured October 26, 2015, to February 8, 2016, and 2016 Lexus ES350 vehicles manufactured
- **caliper_compliance_or_label — CALIPER / compliance or label**: A defect in the caliper whose train-window recalls are dominated by compliance or label.
  Training-source example: Roush Performance Products, Inc. (Roush) is recalling certain model year 2015 Ford Mustang GT Roush Stage 3 vehicles manufactured April 1, 2015, to October 31, 2015, and equipped with Roush Extreme Duty Half Shafts.  The affected vehicles have a brake caliper guide pin that may n
- **master_cylinder_leak — MASTER CYLINDER / leak**: A defect in the master cylinder whose train-window recalls are dominated by leak.
  Training-source example: American Honda Motor Co., Inc. (Honda) is recalling certain model year 2001-2010 and 2012-2015 GL1800, 2001-2005 GL1800A and 2013-2015 GL1800B motorcycles.  The rear brakes of the affected motorcycles may drag after the brakes are released.
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### STEERING

- **electric_power_assist_system_loss_of_control — ELECTRIC POWER ASSIST SYSTEM / loss of control**: A defect in the electric power assist system whose train-window recalls are dominated by loss of control.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2013-2015 Ford Fusion and Lincoln MKZ vehicles manufactured February 3, 2012, to March 20, 2015, and 2015 Ford Edge vehicles manufactured February 26, 2015, to February 28, 2015, and originally sold, or currently registere
- **steering_detachment — STEERING / detachment**: A defect in the steering whose train-window recalls are dominated by detachment.
  Training-source example: Kia Motors America (Kia) is recalling certain 2020 Stinger vehicles equipped with a 2.0L Turbo-GDI engine.  A component within the Rack Mounted Motor Driven Power Steering (MDPS) Assembly may have been manufactured incorrectly, possibly resulting in the steering locking or becomi
- **column_crack_or_fracture — COLUMN / crack or fracture**: A defect in the column whose train-window recalls are dominated by crack or fracture.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain 2020-2021 Toyota Avalon and 2020 Avalon Hybrid, RAV4, and RAV4 Hybrid vehicles.  Breakaway pins within the steering column, designed to absorb energy and reduce injury during a crash, could have been damaged d
- **steering_wheel_handle_bar_detachment — STEERING WHEEL/HANDLE BAR / detachment**: A defect in the steering wheel/handle bar whose train-window recalls are dominated by detachment.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2019 CR-V vehicles.  The metal core of the steering wheel may have burrs which can damage the harnesses routed within, potentially disabling the driver's air bag or causing it to deploy without warning.
- **tie_rod_assembly_loss_of_control — TIE ROD ASSEMBLY / loss of control**: A defect in the tie rod assembly whose train-window recalls are dominated by loss of control.
  Training-source example: BMW of North America, LLC (BMW) is recalling certain 2019 Z4 sDrive30i, 2019-2020 330i xDrive, M340i and M340i xDrive, 2020 X3M and X4M, and Toyota Supra vehicles.  In certain driving conditions, such as high temperatures and rough road surfaces, a steering gear tie rod may becom
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### STRUCTURE

- **roof_and_pillars_failure — ROOF AND PILLARS / failure**: A defect in the roof and pillars whose train-window recalls are dominated by failure.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2019 Honda Ridgeline and Pilot vehicles.  The mounting holes for the clip that secures the right center pillar trim panel may be larger than intended.   In the event of a crash necessitating right side curtain air bag deployme
- **door_compliance_or_label — DOOR / compliance or label**: A defect in the door whose train-window recalls are dominated by compliance or label.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2015-2017 F-150, and 2017 F-250, F-350, F-450, and F-550 vehicles originally produced with black or body colored exterior door handles that may have been subsequently equipped with a chrome exterior door handle cover accessory kit pu
- **trailer_hitches_electrical — TRAILER HITCHES / electrical**: A defect in the trailer hitches whose train-window recalls are dominated by electrical.
  Training-source example: Hyundai Motor America (Hyundai) is recalling certain model year 2016-2017 Tucson vehicles manufactured May 19, 2015, to November 14, 2016, and 2017 Santa Fe vehicles manufactured November 28, 2015, to November 14, 2016.  The affected vehicles may be equipped with an accessory tra
- **structure_compliance_or_label — STRUCTURE / compliance or label**: A defect in the structure whose train-window recalls are dominated by compliance or label.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain model year 2015-2016 Fit LX-trim vehicles manufactured April 11, 2014, to July 02, 2015 and not equipped with a sunroof.  In the affected vehicles, the rear grab handle brackets were not manufactured properly, and as a result,
- **structure_body_compliance_or_label — STRUCTURE BODY / compliance or label**: A defect in the structure body whose train-window recalls are dominated by compliance or label.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2019-2020 Pilot and 2019 Passport vehicles.  The front frame left and right side upper members may not have been welded completely to the unibody.  As such, these vehicles may fail to comply with the requirements of Federal Mo
- **hinge_and_attachments_detachment — HINGE AND ATTACHMENTS / detachment**: A defect in the hinge and attachments whose train-window recalls are dominated by detachment.
  Training-source example: Southeast Toyota Distributors, LLC (SET) is recalling certain 2011-2016 Toyota Tacoma and 4Runner vehicles equipped with accessory hood scoops installed by SET or SET dealers.  The adhesive attaching the hood scoop may weaken, allowing the hood scoop to detach from the vehicle.
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### SUSPENSION

- **rear_crack_or_fracture — REAR / crack or fracture**: A defect in the rear whose train-window recalls are dominated by crack or fracture.
  Training-source example: Hyundai Motor America (Hyundai) is recalling certain model year 2013-2015 Genesis Coupe vehicles manufactured December 28, 2011, to April 6, 2015, equipped with manual transmissions.  In the affected vehicles, if the differential and the suspension rear crossmember were not prope
- **lower_arm_crack_or_fracture — LOWER ARM / crack or fracture**: A defect in the lower arm whose train-window recalls are dominated by crack or fracture.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain 2019-2020 RAV4 and RAV4 Hybrid vehicles.  The front lower suspension arms may have cracks, which may result in the suspension arm separating from the front wheel assembly.
- **suspension_detachment — SUSPENSION / detachment**: A defect in the suspension whose train-window recalls are dominated by detachment.
  Training-source example: Life Line Emergency Vehicles (Life Line) is recalling certain model year 2014-2015 Life Line-modified Ford F-Series emergency vehicles that are equipped with Liquid Spring-brand aftermarket suspension kits. The mounting bracket that attaches the suspension fluid tank to the frame
- **shock_absorber_missing_or_wrong_part — SHOCK ABSORBER / missing or wrong part**: A defect in the shock absorber whose train-window recalls are dominated by missing or wrong part.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain model year 2014 Honda CBR1000S motorcycles manufactured December 9, 2013, to March 28, 2014, and 2015 Honda CBR1000S motorcycles manufactured October 20, 2014, to February 27, 2015.  The affected motorcycles may have been buil
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### TIRES

- **temporary_emergency_spare_tire_compliance_or_label — TEMPORARY/EMERGENCY SPARE TIRE / compliance or label**: A defect in the temporary/emergency spare tire whose train-window recalls are dominated by compliance or label.
  Training-source example: Gulf States Toyota, Inc. (Gulf States) is recalling certain 2017 4Runner , 86, Avalon, Camry, Camry Hybrid, Corolla, Corolla iM, Highlander, Highlander Hybrid, Prius, Prius C, RAV4, RAV4 Hybrid, Sienna  and Yaris vehicles.  The spare tire air pressure was not adjusted to the prop
- **tires_compliance_or_label — TIRES / compliance or label**: A defect in the tires whose train-window recalls are dominated by compliance or label.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain model year 2015 Tacoma pickup trucks manufactured August 7, 2014, to December 22, 2014. The affected vehicles may have had their tires and wheels changed to TRD PRO accessory tires and wheels, causing the infl
- **sidewall_crack_or_fracture — SIDEWALL / crack or fracture**: A defect in the sidewall whose train-window recalls are dominated by crack or fracture.
  Training-source example: Ford Motor Company (Ford) is recalling certain model year 2016 Ford F-250, F-350, F-450, and F-550 trucks manufactured April 5, 2016, to April 11, 2016.  The tires installed during assembly of the affected vehicles may have sustained damage to the inner sidewall, possibly resulti
- **pressure_monitoring_and_regulating_systems_software — PRESSURE MONITORING AND REGULATING SYSTEMS / software**: A defect in the pressure monitoring and regulating systems whose train-window recalls are dominated by software.
  Training-source example: Southeast Toyota Distributors, LLC (SET) is recalling certain model year 2015 Toyota Prius C vehicles manufactured April 20, 2015, to June 30, 2015.  In the affected vehicles, the Tire Pressure Monitoring System (TPMS) may be improperly calibrated and, as a result, the TPMS may f
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### VEHICLE SPEED CONTROL

- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### VISIBILITY

- **defroster_defogger_hvac_system_software — DEFROSTER/DEFOGGER/HVAC SYSTEM / software**: A defect in the defroster/defogger/hvac system whose train-window recalls are dominated by software.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2018-2020 Accord Sedan, Accord Hybrid, and 2019-2020 Insight vehicles.  A software error may cause intermittent or continuous disruptions in communication between the Body Control Module (BCM) and other components.  This may r
- **sun_moon_roof_assembly_detachment — SUN/MOON ROOF ASSEMBLY / detachment**: A defect in the sun/moon roof assembly whose train-window recalls are dominated by detachment.
  Training-source example: Hyundai Motor America (Hyundai) is recalling certain model year 2015-2016 Sonata Hybrid vehicles manufactured December 8, 2014, to August 18, 2015, and Hyundai Sonata vehicles manufactured May 28, 2014, to March 18, 2016, equipped with the panoramic sunroof option.  Due to a bond
- **fan_motor_electrical — FAN/MOTOR / electrical**: A defect in the fan/motor whose train-window recalls are dominated by electrical.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2019 Ranger vehicles previously repaired under recall 19V-726.  The service replacement Heating, Ventilating and Air Conditioning (HVAC) blower motor that was installed may have an improper clearance between an electrical terminal an
- **power_window_devices_and_controls_compliance_or_label — POWER WINDOW DEVICES AND CONTROLS / compliance or label**: A defect in the power window devices and controls whose train-window recalls are dominated by compliance or label.
  Training-source example: Ford Motor Company (Ford) is recalling certain 2018 Ford Expedition and Lincoln Navigator vehicles.  The second row window control modules may intermittently stop the movement of the power window.  If something, such as a finger, is pinched by the window glass, the stopped window
- **rearview_mirrors_devices_sensor_or_signal — REARVIEW MIRRORS/DEVICES / sensor or signal**: A defect in the rearview mirrors/devices whose train-window recalls are dominated by sensor or signal.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2018 Honda Accord and 2019 Honda Insight vehicles.  In certain scenarios, the back-up camera center display may not function properly.  As such, these vehicles fail to comply with the requirements of Federal Motor Vehicle Safe
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### VISIBILITY/WIPER

- **visibility_wiper_software — VISIBILITY/WIPER / software**: A defect in the visibility/wiper whose train-window recalls are dominated by software.
  Training-source example: Honda (American Honda Motor Co.) is recalling certain 2018-2020 Accord Sedan, Accord Hybrid, and 2019-2020 Insight vehicles.  A software error may cause intermittent or continuous disruptions in communication between the Body Control Module (BCM) and other components.  This may r
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

### WHEELS

- **lugs_nuts_bolts_studs_crack_or_fracture — LUGS/NUTS/BOLTS/STUDS / crack or fracture**: A defect in the lugs/nuts/bolts/studs whose train-window recalls are dominated by crack or fracture.
  Training-source example: Southeast Toyota Distributors, LLC (SET) is recalling certain model year 2013-2017 Toyota Tundra and Sequoia vehicles accessorized with Southeast Toyota accessory 20-inch Rockstar wheels installed by Southeast Toyota or a Southeast Toyota dealer.  The Rockstar wheels were install
- **wheels_compliance_or_label — WHEELS / compliance or label**: A defect in the wheels whose train-window recalls are dominated by compliance or label.
  Training-source example: Toyota Motor Engineering & Manufacturing (Toyota) is recalling certain model year 2015 Tacoma pickup trucks manufactured August 7, 2014, to December 22, 2014. The affected vehicles may have had their tires and wheels changed to TRD PRO accessory tires and wheels, causing the infl
- **other_unclear — other/unclear**: No specific label fits, or the narrative is too vague.

