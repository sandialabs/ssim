"""Fixtures that are useful for all tests."""
import pytest


_SIMPLE_DSS = """clear
new object=circuit.DSSLLibtestckt
~ basekv=115 1.00 0.0 60.0 3 20000 21000 4.0 3.0 !edit the voltage source

new loadshape.day 24 1.0
~ mult=(.3 .3 .3 .35 .36 .39 .41 .48 .52 .59 .62 .94 .87 .91 .95 .95 1.0 .98 .94 .92 .61 .60 .51 .44)

new loadshape.year 24 1.0 ! same as day for now
~ mult=".3 .3 .3 .35 .36 .39 .41 .48 .52 .59 .62 .94 .87 .91 .95 .95 1.0 .98 .94 .92 .61 .60 .51 .44"

new loadshape.wind 2400 0.00027777 ! unit must be hours 1.0/3600.0 = .0002777
~ csvfile=zavwind.csv action=normalize ! wind turbine characteristic

! define a linecode for the lines - unbalanced 336 MCM ACSR connection
new linecode.336matrix nphases=3 ! horizontal flat construction
~ rmatrix=(0.0868455 | 0.0298305 0.0887966 | 0.0288883 0.0298305 0.0868455)
! ohms per 1000 ft
~ xmatrix=(0.2025449 | 0.0847210 0.1961452 | 0.0719161 0.0847210 0.2025449)
~ cmatrix=(2.74 | -0.70 2.96| -0.34 -0.71 2.74) !nf per 1000 ft
~ Normamps = 400 Emergamps=600

! Substation transformer
new transformer.sub phases=3 windings=2 buses=(SourceBus subbus)
~ conns='delta wye' kvs="115 12.47 " kvas="20000 20000" XHL=7

! define the lines
new line.line1 subbus loadbus1 linecode=336matrix length=10
new line.line2 loadbus1 loadbus2 336matrix 10
new line.line3 Loadbus2 loadbus3 336matrix 20

! define a couple of loads
new load.load1 bus1=loadbus1 phases=3 kv=12.47 kw=1000.0 pf=0.88 model=1
~ class=1 yearly=year daily=day status=fixed

new load.load2 bus1=loadbus2 phases=3 kv=12.47 kw=500.0 pf=0.88 model=1 class=1
~ yearly=year daily=day conn=delta status=fixed

! Capacitor with control
new capacitor.C1 bus1=loadbus2 phases=3 kvar=600 kv=12.47
new capcontrol.C1 element=line.line3 1 capacitor=C1 type=current ctratio=1
~ ONsetting=60 OFFsetting=55 delay=2

! regulated transformer to DG bus
new transformer.reg1 phases=3 windings=2
~ buses=(loadbus3 regbus)
~ conns='wye wye'
~ kvs="12.47 12.47"
~ kvas="8000 8000"
~ XHL=1 !tiny reactance for a regulator

! Regulator Control definitions
new regcontrol.sub transformer=sub winding=2 vreg=125 band=3 ptratio=60
~ delay=10
new regcontrol.reg1 transformer=reg1 winding=2 vreg=122 band=3 ptratio=60
~ delay=15

! define a wind generator of 8MW
New generator.gen1 bus1=regbus kV=12.47 kW=8000 pf=1 conn=delta daily=wind
~ Model=1

! Define some monitors so's we can see what's happenin'
!New Monitor.gen1a element=generator.gen1 1 mode=48
!New Monitor.line3 element=line.line3 1 mode=48
!New Monitor.gen1 element=generator.gen1 1 mode=32

! Define voltage bases so voltage reports come out in per unit
Set voltagebases="115 12.47 .48"
Calcv
! Set controlmode=time
! Set mode=duty number=2400 hour=0 h=1.0 sec=0 ! Mode resets the monitors
"""

_WIND_DATA = (
    317.611221, 317.3934584, 316.9820228, 316.634582, 316.3729109,
    316.1687186, 315.9720352, 315.7844252, 315.6447931, 315.5911655,
    315.649421, 315.8260992, 316.0869335, 316.4135473, 316.8646908,
    317.4613432, 318.1546745, 318.9159842, 319.7142778, 320.5764724,
    321.4848611, 322.3857204, 323.2943744, 324.2005717, 325.0228072,
    325.7582195, 326.4574623, 327.1545938, 327.8373202, 328.456899,
    328.971953, 329.4780338, 330.064323, 330.6542936, 331.2055507,
    331.7582721, 332.3484507, 333.0012139, 333.7047665, 334.4293088,
    335.1897159, 335.9894139, 336.8417877, 337.7659857, 338.718766,
    339.6596063, 340.5863827, 341.5051753, 342.4016454, 343.2477905,
    344.0426362, 344.800403, 345.552618, 346.34701, 347.1742329,
    347.9577324, 348.6402199, 349.2785853, 349.9234434, 350.5397499,
    351.1749116, 351.8826603, 352.6179414, 353.3420889, 354.0423776,
    354.675121, 355.1940724, 355.595285, 355.8719405, 356.0502621,
    356.1958229, 356.2969301, 356.3012957, 356.2322802, 356.1157936,
    355.9343268, 355.6882099, 355.3840449, 355.0660231, 354.7719498,
    354.4917731, 354.2694636, 354.1204022, 354.0252401, 353.9875099,
    354.0238031, 354.1487384, 354.3344429, 354.5415912, 354.7222581,
    354.8708427, 354.9610423, 354.9558196, 354.8829066, 354.7701194,
    354.5877984, 354.2927209, 353.9128942, 353.4554087, 352.9227427,
    352.3695569, 351.8298458, 351.3234432, 350.8942715, 350.5567209,
    350.3016111, 350.1281339, 349.9933121, 349.9037604, 349.933974,
    350.0916978, 350.2976477, 350.482362, 350.6438416, 350.8099452,
    350.9677231, 351.0887272, 351.1512477, 351.1371018, 351.0606868,
    350.9315375, 350.7666793, 350.5350191, 350.2087533, 349.8583349,
    349.5394447, 349.2628875, 349.0258527, 348.7893316, 348.4949828,
    348.1402907, 347.7949519, 347.4901635, 347.182116, 346.8367913,
    346.5005382, 346.2330092, 346.0103608, 345.8457513, 345.7695885,
    345.7166572, 345.6109926, 345.4821094, 345.3874429, 345.2720943,
    345.0888217, 344.8592514, 344.5587883, 344.1690284, 343.7259924,
    343.2344491, 342.72763, 342.2583851, 341.8271744, 341.3984756,
    340.9402, 340.5052745, 340.1540393, 339.845067, 339.512728,
    339.1471301, 338.7532169, 338.3302325, 337.8869051, 337.4692697,
    337.105052, 336.7615711, 336.4072434, 336.0118346, 335.5554534,
    335.0460678, 334.4796351, 333.8640881, 333.2309723, 332.576354,
    331.8879942, 331.1749713, 330.4601717, 329.7383977, 328.9525141,
    328.0536173, 327.1385299, 326.3305388, 325.621051, 324.9915441,
    324.4630105, 324.0290234, 323.6678014, 323.4152145, 323.2820229,
    323.2666228, 323.3137502, 323.3256705, 323.2898721, 323.243634,
    323.1962768, 323.0886311, 322.9099656, 322.7200331, 322.5394761,
    322.3408046, 322.1216257, 321.8971484, 321.6461823, 321.3526632,
    321.0525791, 320.7602967, 320.4161619, 319.980845, 319.5298089,
    319.0470693, 318.5518381, 318.0871316, 317.6459096, 317.2175813,
    316.8391603, 316.5116783, 316.2373934, 316.0336365, 315.8571726,
    315.6784223, 315.4968247, 315.3266443, 315.2014069, 315.1167946,
    315.0704795, 315.0862512, 315.1574192, 315.2823622, 315.4633297,
    315.6541861, 315.8774842, 316.1854004, 316.5776987, 317.1085645,
    317.8065414, 318.6195897, 319.5356429, 320.6339787, 321.8948353,
    323.2776315, 324.7410167, 326.2064713, 327.6462691, 329.0468246,
    330.3934967, 331.6492364, 332.8636088, 334.06594, 335.1700272,
    336.1918425, 337.2325233, 338.2625671, 339.1864043, 339.9931219,
    340.7118734, 341.3753739, 342.0248694, 342.6431727, 343.1883617,
    343.659619, 344.0670805, 344.4268343, 344.7691978, 345.1074606,
    345.4216215, 345.7092185, 346.0248438, 346.4083703, 346.8472629,
    347.3017418, 347.7395839, 348.209115, 348.7247928, 349.2207777,
    349.6756934, 350.0981775, 350.5069697, 350.9240719, 351.3287989,
    351.6911235, 352.0317183, 352.4035843, 352.8119535, 353.2271476,
    353.6378763, 354.0392756, 354.4402162, 354.8213718, 355.1629829,
    355.5069158, 355.9406974, 356.4897034, 357.0762646, 357.6679469,
    358.3057239, 359.002645, 359.7415991, 360.5376987, 361.4489953,
    362.4821741, 363.5806712, 364.7109943, 365.9049041, 367.2845317,
    368.8651725, 370.5628678, 372.3370309, 374.1708618, 376.1215257,
    378.0035116, 379.9838066, 381.9632997, 383.8430613, 385.5815836,
    387.2212823, 388.770991, 390.2190378, 391.5800707, 392.8204068,
    393.8904215, 394.8634716, 395.8004329, 396.731718, 397.7227421,
    398.7106351, 399.6277421, 400.5195753, 401.3806723, 402.1839825,
    402.964365, 403.7927355, 404.7108016, 405.6703004, 406.6381453,
    407.6260687, 408.6300961, 409.6670957, 410.7605834, 411.9240984,
    413.2439916, 414.7358244, 416.2754785, 417.8339106, 419.4646045,
    421.1863129, 422.9374771, 424.6419112, 426.3544735, 428.1149452,
    429.8810879, 431.6440843, 433.8480445, 436.166157, 438.4449427,
    440.6215847, 442.6911698, 444.6132396, 446.4168445, 448.0876621,
    449.5439678, 450.8442749, 452.0938832, 453.3281022, 454.5529435,
    455.7627513, 456.9651945, 458.2117725, 459.4894225, 460.7567922,
    462.0172313, 463.2805955, 464.5191916, 465.6892265, 466.7434241,
    467.6671813, 468.5000481, 469.339979, 470.3286942, 471.4372634,
    472.5550912, 473.7218552, 474.9969274, 476.3683617, 477.8548709,
    479.5135069, 481.3119248, 483.1393606, 485.0171723, 487.0596347,
    489.3174658, 491.7098166, 494.0635211, 496.2776889, 498.3868897,
    500.4666678, 502.4794962, 504.4408697, 506.8468175, 508.7448068,
    510.0975066, 511.1952655, 512.3429606, 513.4837867, 514.3806776,
    514.9931067, 515.5892733, 516.2332475, 516.9110407, 517.6991601,
    518.4202984, 519.0768557, 519.8778024, 520.8554274, 522.0493416,
    523.5465732, 525.1242822, 526.4808652, 527.7612395, 529.1267265,
    530.4868092, 531.69557, 532.7530518, 533.6272415, 534.1502199,
    534.3837794, 534.5268267, 534.6011122, 534.5886081, 534.5912579,
    534.577621, 534.5741991, 534.6634503, 534.9200335, 535.4270964,
    536.0370646, 536.6719452, 537.4304546, 538.2487631, 539.0877106,
    540.1562644, 541.4250174, 542.6969594, 543.9426341, 545.1346847,
    546.1793603, 547.0368934, 547.7385593, 548.2318942, 548.4049494,
    548.2950937, 548.1071318, 548.035848, 548.0805003, 548.0337458,
    547.8183486, 547.6109906, 547.4438871, 547.2053406, 546.8569864,
    546.3049423, 545.6371485, 544.9137751, 543.9716779, 542.8253795,
    541.5726297, 540.2458396, 538.8615766, 537.4982964, 536.1552061,
    534.80494, 533.6364495, 532.8171227, 532.3301243, 532.070822,
    531.8855761, 531.7209792, 531.5275848, 531.1169432, 530.4592843,
    529.6771404, 528.9838435, 528.4977117, 528.1524484, 527.929931,
    527.7892907, 527.7434924, 527.9164499, 528.4541756, 529.3499885,
    530.4244489, 531.6333325, 533.0877195, 534.9711723, 537.305879,
    539.8417938, 542.4814429, 545.1840171, 547.8019698, 550.4414272,
    553.4231897, 556.5000505, 559.1450774, 561.425236, 563.5883198,
    565.5837853, 567.3652863, 569.0335515, 570.5219483, 571.7708615,
    572.9202893, 574.0936362, 575.3051478, 576.4950095, 577.5064544,
    578.2344623, 578.7636967, 579.1935296, 579.5068961, 579.602123,
    579.360326, 578.7938702, 577.9012817, 576.6614021, 575.4358114,
    574.6053005, 574.1000944, 573.8203872, 573.6960868, 573.4312216,
    572.8043536, 571.9630597, 571.2655693, 570.9233358, 570.8858961,
    571.0232721, 571.1602028, 571.077512, 570.7262499, 570.1562906,
    569.4633304, 568.8183569, 568.3287066, 568.0349861, 567.9794176,
    568.031023, 567.9570246, 567.7978152, 567.6723462, 567.6278388,
    567.6652993, 567.4671093, 566.7902829, 565.7680041, 564.4804168,
    562.9633693, 561.2535194, 559.3019473, 557.1897163, 555.0443663,
    552.8975512, 550.8417024, 548.8651413, 546.891108, 544.9239117,
    542.8907148, 540.7808854, 538.7167002, 536.7930289, 534.9997597,
    533.2267015, 531.4454574, 529.6995904, 528.0037078, 526.3599885,
    524.7345651, 523.1926867, 521.6766413, 519.9897179, 518.1887424,
    516.5012466, 515.1238354, 514.0661158, 513.1393467, 512.1824058,
    511.0566531, 509.6600821, 508.1141007, 506.6092494, 505.165051,
    503.8215337, 502.8572886, 501.7782799, 500.5990138, 499.4148623,
    498.2475421, 497.0162488, 495.6898994, 494.3165955, 492.95127,
    491.5758229, 490.2206383, 488.9517525, 487.7527406, 486.5830714,
    485.4620002, 484.4879617, 483.7080712, 483.0807511, 482.5542874,
    482.093254, 481.676026, 481.3250921, 481.0690563, 480.9276143,
    480.9493007, 481.1440595, 481.5056233, 482.029255, 482.6403725,
    483.2980626, 484.0116328, 484.7580366, 485.4792315, 486.0794053,
    486.5549444, 487.0483729, 487.5687497, 488.0017283, 488.3358968,
    488.6570237, 488.958642, 489.1700866, 489.2806858, 489.2163557,
    488.9508243, 488.5695372, 488.1491249, 487.7077154, 487.2572877,
    486.7971992, 486.3580488, 486.0387292, 485.853327, 485.7052352,
    485.5259689, 485.3421118, 485.2040624, 485.1338892, 485.1856584,
    485.3345567, 485.4172961, 485.4155782, 485.3723103, 485.2622521,
    485.1761878, 485.2279262, 485.3990906, 485.6053527, 485.7619796,
    485.8115984, 485.7750274, 485.6682356, 485.4097829, 484.9368807,
    484.2767064, 483.5357427, 482.801764, 482.0724307, 481.3195345,
    480.5141093, 479.6942858, 478.93073, 478.2031016, 477.4493429,
    476.6413398, 475.810334, 475.0434508, 474.3400198, 473.5755215,
    472.7056639, 471.8806537, 471.2258003, 470.7125241, 470.290246,
    469.9207585, 469.6122028, 469.4048051, 469.2651395, 469.1679,
    469.1776423, 469.3231118, 469.5654977, 469.8246851, 470.115127,
    470.5034321, 470.8677313, 471.1386447, 471.402299, 471.6418463,
    471.7994264, 471.8634352, 471.7817221, 471.4721432, 470.9395242,
    470.2876375, 469.5993527, 468.8948745, 468.1407963, 467.3076878,
    466.3983673, 465.3785674, 464.2053819, 462.9241514, 461.5708889,
    460.1713846, 458.7942848, 457.4151393, 455.9650455, 454.3850149,
    452.6316255, 450.7813834, 448.9527887, 447.1608231, 445.3235811,
    443.4015672, 441.4336481, 439.4222335, 437.3745254, 435.3342671,
    433.3074375, 431.4748363, 429.9751574, 428.4414026, 426.8696469,
    425.3057847, 423.7624658, 422.2448151, 420.7765875, 419.3378495,
    417.9217517, 416.5530972, 415.1810584, 413.7231887, 412.1885758,
    410.6338543, 409.0943379, 407.5781475, 406.0492847, 404.4813147,
    402.8812146, 401.223608, 399.4883216, 397.731101, 396.0197985,
    394.3474405, 392.6587597, 390.9383516, 389.1958378, 387.4293348,
    385.6152502, 383.7615095, 381.9504127, 380.2190477, 378.5105577,
    376.7894508, 374.9468016, 373.0190007, 371.1042351, 369.1826631,
    367.269687, 365.4424234, 363.7403128, 362.1493228, 360.6686908,
    359.2763962, 357.9244334, 356.6139775, 355.4065585, 354.3176424,
    353.325406, 352.4103433, 351.5654921, 350.7546875, 349.9085806,
    349.0234134, 348.0941943, 347.1166236, 346.1415101, 345.1840883,
    344.2528979, 343.373414, 342.5168811, 341.6792578, 340.8987781,
    340.1728862, 339.4886751, 338.8429894, 338.1934852, 337.4854143,
    336.6997328, 335.8896288, 335.1250289, 334.3688818, 333.6175803,
    332.9769693, 332.4815678, 332.084844, 331.7556479, 331.4927415,
    331.3290615, 331.2493172, 331.1910379, 331.1275167, 331.0597529,
    330.9546597, 330.7453713, 330.4379344, 330.0691967, 329.6320639,
    329.1054253, 328.5238699, 327.9737381, 327.493566, 327.0716301,
    326.6833579, 326.3017082, 325.9318717, 325.5630236, 325.1787794,
    324.8078129, 324.4703264, 324.197316, 323.9983206, 323.846861,
    323.7359524, 323.6421575, 323.5210622, 323.3517589, 323.1395506,
    322.9109348, 322.6407582, 322.291123, 321.8935113, 321.4634633,
    320.9806008, 320.4273271, 319.8140476, 319.1737529, 318.4768015,
    317.7278672, 316.9577203, 316.1711663, 315.3540139, 314.5249791,
    313.6806428, 312.7961357, 311.8959321, 311.0543357, 310.2798364,
    309.5289363, 308.7624476, 307.9309336, 307.0242949, 306.0560262,
    305.0408655, 304.0211372, 303.0467672, 302.139058, 301.2671206,
    300.3787138, 299.5000692, 298.6800006, 297.9286472, 297.2228528,
    296.5174462, 295.8234623, 295.184532, 294.6408935, 294.2120342,
    293.8671451, 293.5178719, 293.1473482, 292.8025216, 292.461744,
    292.1031426, 291.7106234, 291.2737693, 290.8408895, 290.4316523,
    290.0167181, 289.5791388, 289.0918814, 288.5726632, 288.068019,
    287.5806111, 287.1026701, 286.6067143, 286.0796305, 285.5404335,
    285.0111593, 284.5523404, 284.1749822, 283.8219725, 283.4938333,
    283.2111591, 282.9684717, 282.7831994, 282.6934238, 282.7117701,
    282.8269861, 282.9940944, 283.1459859, 283.2358865, 283.2739265,
    283.3036103, 283.3147104, 283.2610689, 283.136489, 282.9681272,
    282.757115, 282.4831318, 282.1443357, 281.7872252, 281.4700782,
    281.2077261, 280.9944158, 280.8151549, 280.6290175, 280.382319,
    280.0651821, 279.7221465, 279.3870724, 279.0597154, 278.7814239,
    278.589243, 278.4205982, 278.2454649, 278.103489, 277.9996842,
    277.8933919, 277.7744969, 277.6817423, 277.6201686, 277.5701791,
    277.5344472, 277.5404833, 277.6406436, 277.8499803, 278.1120972,
    278.3828219, 278.6782364, 279.0093962, 279.355548, 279.7215832,
    280.1274034, 280.5844894, 281.0912884, 281.6039856, 282.1060812,
    282.6471215, 283.2254381, 283.819901, 284.45444, 285.1267909,
    285.824525, 286.5537575, 287.2969292, 288.0456001, 288.8417737,
    289.6806056, 290.5143956, 291.3506882, 292.2272025, 293.1956221,
    294.2855015, 295.4706396, 296.7348631, 298.0490482, 299.395079,
    300.7880309, 302.170728, 303.5056402, 304.8415434, 306.1862783,
    307.5029003, 308.7780047, 309.9972189, 311.1309035, 312.1851246,
    313.2130098, 314.2332453, 315.2317514, 316.2005163, 317.1291295,
    318.0331731, 318.9058318, 319.7111289, 320.509465, 321.3321911,
    322.1689318, 322.9882073, 323.7200664, 324.3222933, 324.8181172,
    325.2289672, 325.5769922, 325.8801942, 326.1378383, 326.373687,
    326.5462927, 326.6513106, 326.7953913, 327.0363406, 327.3959037,
    327.8823519, 328.4344905, 328.9543591, 329.4117185, 329.8306842,
    330.2501615, 330.7004683, 331.1871476, 331.7330583, 332.373395,
    333.0984867, 333.844917, 334.5880437, 335.3478147, 336.1060288,
    336.8872109, 337.7241355, 338.585327, 339.4305702, 340.2389897,
    341.0026074, 341.6747757, 342.2758473, 342.9013187, 343.5792188,
    344.2829163, 344.9707603, 345.6277766, 346.2541108, 346.8478238,
    347.3948722, 347.8716734, 348.2761995, 348.5996054, 348.8409078,
    349.0014736, 349.0554233, 348.981119, 348.7834813, 348.4606273,
    348.0033347, 347.4295963, 346.7491383, 345.9670667, 345.0683234,
    344.0156943, 342.9040274, 341.8573084, 340.8692525, 339.8902345,
    338.9035844, 337.9210795, 336.9499745, 335.9844155, 335.0372599,
    334.1409048, 333.2611363, 332.3070255, 331.2287579, 330.0386379,
    328.7329325, 327.2905443, 325.7363867, 324.1054649, 322.401708,
    320.6286145, 318.9486101, 317.3598242, 315.8049158, 314.2537161,
    312.6897044, 311.1280539, 309.567095, 307.9967593, 306.3947147,
    304.7898882, 303.2421429, 301.7254228, 300.1866501, 298.6147156,
    297.0218115, 295.4456211, 293.9191301, 292.4743376, 291.1387495,
    289.8705786, 288.6185635, 287.3974729, 286.2312575, 285.0979701,
    283.9695471, 282.8250959, 281.662151, 280.5055797, 279.3483464,
    278.1682891, 276.9593767, 275.7332168, 274.4883147, 273.2101723,
    271.9236797, 270.6328136, 269.2831187, 267.8331068, 266.3228069,
    264.7390551, 263.136805, 261.5657171, 259.9732568, 258.3853526,
    256.8862812, 255.4818893, 254.1674549, 252.9581499, 251.8149075,
    250.7184944, 249.6265077, 248.4707601, 247.2906372, 246.125243,
    244.9643807, 243.8348138, 242.7462404, 241.6834731, 240.6596064,
    239.6452236, 238.6090174, 237.5670523, 236.5057714, 235.4224198,
    234.3808071, 233.4330493, 232.5281441, 231.5697308, 230.5693647,
    229.5981671, 228.6245822, 227.6178199, 226.6067938, 225.6152679,
    224.656625, 223.7223874, 222.8020759, 221.8512966, 220.896108,
    219.9294281, 218.9649665, 218.0566484, 217.2137724, 216.4179149,
    215.6718801, 214.9556922, 214.2392254, 213.5237042, 212.8287749,
    212.1521461, 211.4562748, 210.734618, 210.0068418, 209.2426987,
    208.4036656, 207.4929427, 206.544214, 205.6030035, 204.6746495,
    203.7580975, 202.9046457, 202.1304953, 201.3986849, 200.7114431,
    200.0753075, 199.4918579, 198.9846485, 198.5376294, 198.1027737,
    197.6559826, 197.2440154, 196.9338368, 196.7153076, 196.5505901,
    196.4448922, 196.4110273, 196.424028, 196.4810823, 196.6301864,
    196.8877793, 197.2518698, 197.7107691, 198.256672, 198.9366557,
    199.7804604, 200.8138997, 202.0526701, 203.4320464, 204.9081583,
    206.498264, 208.1207506, 209.6597956, 211.0873995, 212.42274,
    213.6411073, 214.7067567, 215.6771322, 216.5908507, 217.4512731,
    218.2764056, 219.080415, 219.8755141, 220.6818928, 221.4978338,
    222.3129811, 223.1422014, 223.9858292, 224.8918082, 225.7739718,
    226.6883973, 227.6771087, 228.6740915, 229.61194, 230.4759051,
    231.290101, 232.0988432, 232.8753503, 233.5598552, 234.1927277,
    234.8393655, 235.5070496, 236.185888, 236.8681132, 237.5428691,
    238.2094401, 238.8938448, 239.595301, 240.2924227, 240.9944436,
    241.7046044, 242.3848185, 243.0151246, 243.5774594, 244.055407,
    244.4848522, 244.89607, 245.292863, 245.6255118, 245.8450308,
    245.9744153, 246.0586488, 246.1192511, 246.169544, 246.2194061,
    246.25788, 246.2642184, 246.1898566, 246.0510811, 245.9190565,
    245.8063038, 245.6914133, 245.5679024, 245.4713564, 245.3997063,
    245.3247004, 245.2517421, 245.1984063, 245.1756203, 245.1579635,
    245.1125236, 245.0565218, 245.0149678, 244.9770004, 244.9640592,
    244.9965565, 245.0281767, 245.0036212, 244.9251027, 244.8120872,
    244.6533716, 244.4403578, 244.1845259, 243.9092034, 243.6118918,
    243.2675758, 242.8999959, 242.5588386, 242.2560744, 241.9694881,
    241.658676, 241.2912789, 240.8781841, 240.4501162, 240.0024381,
    239.528292, 239.0319495, 238.5204483, 238.0263714, 237.5286319,
    236.9462781, 236.2727038, 235.5683731, 234.8681176, 234.1742117,
    233.4762517, 232.7567602, 232.0184813, 231.2953425, 230.5972087,
    229.9369781, 229.3794096, 228.9324091, 228.5775002, 228.3191235,
    228.1269597, 228.0215359, 228.0613175, 228.2300395, 228.471636,
    228.7753931, 229.1377571, 229.5522504, 230.008282, 230.4713026,
    230.9677929, 231.534919, 232.1485626, 232.816978, 233.5810166,
    234.4334116, 235.2987774, 236.1294451, 236.9496854, 237.770673,
    238.6077578, 239.4985614, 240.4268531, 241.3373216, 242.2103721,
    243.069948, 243.9383103, 244.8005729, 245.6411821, 246.4570981,
    247.2455987, 247.9976108, 248.7116619, 249.4271824, 250.1971733,
    251.0623442, 251.9952795, 252.9240813, 253.8187246, 254.6634158,
    255.471989, 256.2835934, 257.0735931, 257.8022845, 258.4893594,
    259.1670236, 259.8390549, 260.4947953, 261.12849, 261.7619447,
    262.43734, 263.1474033, 263.8635461, 264.5486194, 265.1839073,
    265.825572, 266.4858848, 267.1264065, 267.7288108, 268.2914836,
    268.8111457, 269.2677017, 269.6525528, 269.9450714, 270.1301193,
    270.1979384, 270.1581006, 270.065897, 269.9472358, 269.7859898,
    269.5958612, 269.3890254, 269.1127534, 268.7346594, 268.3153751,
    267.9078899, 267.5193193, 267.1593008, 266.8187442, 266.4412496,
    266.0364414, 265.664443, 265.3341459, 265.0360397, 264.7333243,
    264.3814212, 264.0127859, 263.6847149, 263.4238494, 263.2290761,
    263.0908315, 263.0335587, 263.0639513, 263.1707919, 263.3131451,
    263.4312238, 263.5298658, 263.6451181, 263.7824501, 263.9461053,
    264.148716, 264.359517, 264.5574839, 264.767398, 264.9708115,
    265.1042577, 265.1454252, 265.100977, 265.0128881, 264.9605434,
    264.9678834, 265.003649, 265.016533, 265.0022042, 265.0280489,
    265.1120806, 265.2193759, 265.3198271, 265.3574254, 265.3195269,
    265.2563694, 265.2076168, 265.21483, 265.2550988, 265.2570605,
    265.2119376, 265.1192539, 264.9836952, 264.8171062, 264.5981134,
    264.3161736, 264.002305, 263.6867319, 263.356652, 263.0012787,
    262.597841, 262.1660862, 261.786342, 261.4991474, 261.3163101,
    261.2393036, 261.2428364, 261.2638719, 261.2540105, 261.2354859,
    261.2722523, 261.3864293, 261.5174389, 261.6175473, 261.6911403,
    261.7680103, 261.8904168, 262.067816, 262.3025313, 262.5967583,
    262.9229038, 263.199472, 263.370798, 263.4623355, 263.4996796,
    263.4938325, 263.4609674, 263.3879372, 263.213394, 262.9117656,
    262.5323858, 262.1147773, 261.6565556, 261.1659091, 260.6299813,
    260.0243322, 259.3861302, 258.7698447, 258.1956815, 257.6740427,
    257.2079579, 256.7609356, 256.2912163, 255.8018249, 255.314551,
    254.8279766, 254.3308758, 253.8150203, 253.2855891, 252.7683902,
    252.286103, 251.8034772, 251.2769945, 250.7522951, 250.2762804,
    249.8421646, 249.422919, 248.995488, 248.5536377, 248.0821332,
    247.5730372, 247.0964037, 246.7221541, 246.4693729, 246.3482118,
    246.3411968, 246.4525004, 246.7160444, 247.1197238, 247.6082286,
    248.1424719, 248.611686, 248.9369285, 249.164655, 249.3312934,
    249.4380866, 249.4729642, 249.4486077, 249.3532638, 249.1435313,
    248.8222358, 248.4468141, 248.0855669, 247.789498, 247.5510333,
    247.3546101, 247.2335696, 247.195084, 247.2194155, 247.2786051,
    247.344078, 247.3342602, 247.201547, 246.9778273, 246.6541864,
    246.2171009, 245.6703233, 245.0163473, 244.2451434, 243.3542169,
    242.3661182, 241.3929461, 240.5269726, 239.7509902, 239.0569044,
    238.4661323, 238.0022348, 237.6607673, 237.4221312, 237.2695715,
    237.1912402, 237.1480636, 237.1158755, 237.0985975, 237.0618517,
    236.9628409, 236.790104, 236.5904318, 236.4088174, 236.238672,
    236.056044, 235.831688, 235.5585787, 235.2415196, 234.874795,
    234.4473613, 233.9612583, 233.4360322, 232.9084871, 232.4064765,
    231.933118, 231.4758506, 230.9896967, 230.4643014, 229.9282315,
    229.4019896, 228.896304, 228.3525542, 227.7220378, 227.0587817,
    226.4148608, 225.812764, 225.2522211, 224.7285631, 224.2775189,
    223.9242194, 223.6522489, 223.4255293, 223.2595153, 223.1721794,
    223.1637783, 223.1628609, 223.1025106, 223.0115737, 222.9461273,
    222.9150859, 222.8912832, 222.8714087, 222.8637289, 222.8505004,
    222.8204338, 222.8256794, 222.8864375, 222.97525, 223.0989814,
    223.2637184, 223.4814377, 223.7576173, 224.0366838, 224.3084215,
    224.5978551, 224.9175826, 225.2753902, 225.6780022, 226.1215833,
    226.6346475, 227.2351848, 227.8999622, 228.629579, 229.4094478,
    230.1929066, 230.9783469, 231.7788824, 232.6277683, 233.5417047,
    234.4732154, 235.3905862, 236.3155136, 237.2834995, 238.3354135,
    239.4942242, 240.6975971, 241.8928961, 243.0987499, 244.2961625,
    245.4821849, 246.7002569, 247.9455002, 249.1716137, 250.3541261,
    251.5317211, 252.7251249, 253.9279135, 255.1586391, 256.4295559,
    257.7296002, 259.0077984, 260.2535174, 261.4909087, 262.7131949,
    263.967883, 265.2639573, 266.5256544, 267.7532616, 268.9824646,
    270.1404191, 271.2177978, 272.234585, 273.1914165, 274.0828746,
    274.9160979, 275.7066648, 276.4680843, 277.2182902, 277.9545132,
    278.6314949, 279.2489131, 279.8525813, 280.4473789, 281.000552,
    281.51881, 282.0506, 282.628273, 283.2803971, 284.0164007,
    284.8301679, 285.673206, 286.4937377, 287.3377005, 288.1974879,
    289.0096987, 289.7784507, 290.5284127, 291.2922393, 292.0907894,
    292.9101301, 293.7220028, 294.5189345, 295.3241547, 296.1344395,
    296.8763858, 297.5408804, 298.242372, 299.0568898, 299.9903024,
    301.0300957, 302.1319578, 303.2380967, 304.3208497, 305.4063233,
    306.5548018, 307.7698937, 309.0524453, 310.3927787, 311.7128286,
    312.9963234, 314.3015048, 315.6528363, 316.9966729, 318.2622905,
    319.4435208, 320.6541237, 321.9601719, 323.2889406, 324.539072,
    325.7072963, 326.900297, 328.1512425, 329.3855784, 330.6055508,
    331.8533578, 333.0544639, 334.1612874, 335.1880001, 336.1435195,
    337.0145966, 337.7918141, 338.5487055, 339.3059912, 339.9934873,
    340.578461, 341.0699306, 341.5140016, 341.9647451, 342.3964692,
    342.7759371, 343.125245, 343.4134099, 343.6178031, 343.7676237,
    343.8934549, 344.055035, 344.2339972, 344.3616862, 344.4230652,
    344.3998698, 344.3044019, 344.1687684, 344.0068647, 343.8651107,
    343.7278589, 343.5592564, 343.3688157, 343.1269923, 342.8237394,
    342.4783816, 342.0765009, 341.6039507, 341.0791102, 340.5283936,
    339.9592068, 339.4023149, 338.8770632, 338.3507513, 337.8721863,
    337.4974712, 337.1698943, 336.8623776, 336.5821502, 336.3243607,
    336.1209836, 335.9775101, 335.8794069, 335.8755881, 335.9957299,
    336.1909794, 336.4278602, 336.7204208, 337.0594487, 337.4317427,
    337.8669657, 338.3417497, 338.8050823, 339.2586512, 339.7360869,
    340.2307756, 340.6958553, 341.1156349, 341.4731097, 341.7589813,
    341.9997159, 342.241402, 342.530491, 342.8537204, 343.1706777,
    343.4792288, 343.8134027, 344.2252822, 344.6999656, 345.1688113,
    345.6222324, 346.066592, 346.4528794, 346.7400108, 346.9548617,
    347.1178913, 347.2296871, 347.3194563, 347.3941733, 347.4032215,
    347.277068, 347.0487788, 346.8451519, 346.7120427, 346.5913708,
    346.4725699, 346.374678, 346.3124835, 346.3650314, 346.5338571,
    346.7402055, 346.9497364, 347.1239812, 347.2076981, 347.2085075,
    347.1667253, 347.0605982, 346.8432045, 346.4959294, 346.0620653,
    345.5767845, 345.0424235, 344.4612429, 343.8183626, 343.0897673,
    342.2615822, 341.38517, 340.5063417, 339.6320712, 338.7688039,
    337.9222226, 337.1278178, 336.3712354, 335.6091893, 334.8720899,
    334.1625688, 333.4168675, 332.5992221, 331.7457423, 330.9080489,
    330.0857707, 329.2120106, 328.2338765, 327.1409846, 325.9365588,
    324.6263291, 323.1859213, 321.6113564, 319.9131806, 318.2348154,
    316.4431778, 314.6093666, 312.8207259, 311.0739282, 309.3457775,
    307.6784957, 306.0753067, 304.4812323, 302.9160322, 301.4292068,
    300.0136666, 298.6422666, 297.3028631, 295.975678, 294.6471692,
    293.3062622, 291.9353007, 290.5483058, 289.1818377, 287.8514961,
    286.514604, 285.1043139, 283.6163456, 282.1265595, 280.6778053,
    279.2746908, 277.9188184, 276.5671579, 275.2341016, 273.9724564,
    272.7597113, 271.5636794, 270.3775421, 269.2085883, 268.0637348,
    266.9737272, 265.9319251, 264.912556, 263.8892072, 262.8759018,
    261.9163886, 261.0011697, 260.0795169, 259.1490507, 258.2487171,
    257.3783254, 256.493752, 255.5507991, 254.5174281, 253.4047208,
    252.2179266, 250.9920208, 249.7875314, 248.6350939, 247.5647808,
    246.5737632, 245.6556623, 244.8188647, 244.0540996, 243.3408124,
    242.652163, 241.9622867, 241.2772995, 240.6113073, 239.9431107,
    239.2635926, 238.6160521, 238.0030535, 237.3988175, 236.8292267,
    236.3029733, 235.8067803, 235.3281182, 234.8158203, 234.2328983,
    233.6151493, 232.9995317, 232.3683561, 231.7264715, 231.1120683,
    230.5273867, 229.9439144, 229.365873, 228.811564, 228.2598086,
    227.6823019, 227.0665786, 226.4155992, 225.7361079, 225.0157024,
    224.2369685, 223.486947, 222.7737798, 222.0999808, 221.5059594,
    220.9958958, 220.5684509, 220.221676, 219.9506553, 219.7353795,
    219.5480049, 219.3806989, 219.2415372, 219.128622, 219.0158973,
    218.8824067, 218.7291552, 218.5825585, 218.4490931, 218.303484,
    218.1215857, 217.9300932, 217.7854415, 217.7236376, 217.7583505,
    217.9121764, 218.1993081, 218.6020873, 219.1419326, 219.8461145,
    220.7329385, 221.7489375, 222.8167684, 223.9314083, 225.1793235,
    226.4774472, 227.8341006, 229.2552408, 230.7346211, 232.251231,
    233.8254892, 235.5062929, 237.2810305, 239.1091467, 240.9862575,
    242.8879317, 244.7676665, 246.6133174, 248.4845854, 250.4160052,
    252.3543798, 254.2345486, 256.0357559, 257.773164, 259.4203246,
    260.9720252, 262.4878679, 264.0176263, 265.5383001, 266.9800096,
    268.321133, 269.5509909, 270.6856626, 271.7855956, 272.8597336,
    273.8977761, 274.9412808, 275.9975853, 277.0193267, 278.0209995,
    279.0072982, 279.9498191, 280.8404872, 281.6680583, 282.4642367,
    283.2545518, 283.9788604, 284.5959838, 285.1255583, 285.6071977,
    286.0754026, 286.5829923, 287.1907471, 287.9210069, 288.78028,
    289.729196, 290.7373586, 291.8327903, 293.0157131, 294.2943927,
    295.7279329, 297.2808599, 298.8778108, 300.5077014, 302.0965534,
    303.5842781, 305.0424802, 306.4871821, 307.8890614, 309.3241761,
    310.8352045, 312.385514, 313.9095144, 315.3747522, 316.8527584,
    318.372234, 319.9020675, 321.6116472, 323.3826286, 325.182802,
    327.0039737, 328.7889177, 330.4967237, 332.1444326, 333.6924265,
    335.0392001, 336.1706914, 337.1667417, 338.062197, 338.8916361,
    339.6880017, 340.4979624, 341.3709712, 342.2879241, 343.2360148,
    344.2697583, 345.4322667, 346.6501163, 347.8369301, 349.0428634,
    350.3870902, 351.9274544, 353.6732263, 355.5594626, 357.5072193,
    359.535671, 361.5679821, 363.4703084, 365.3272363, 367.3046097,
    369.3467158, 371.24687, 372.9513265, 374.5518331, 376.0648196,
    377.3005907, 378.4929432, 379.7112075, 380.9461543, 382.1278971,
    383.2362348, 384.3029929, 385.3326017, 386.3337334, 387.331304,
    388.2683806, 389.0840884, 389.8387843, 390.561173, 391.2029666,
    391.7675435, 392.2991643, 392.841871, 393.4805153, 394.2296761,
    394.9677335, 395.6663835, 396.3938603, 397.1310142, 397.8571072,
    398.6023839, 399.4100834, 400.2992364, 401.232283, 402.1997253,
    403.2271212, 404.3311552, 405.5200032, 406.7709, 408.0766553,
    409.4343983, 410.7997174, 412.1594565, 413.5674971, 415.0373768,
    416.5489634, 418.1435463, 419.8677645, 421.7534476, 423.8307388,
    426.0634274, 428.2272992, 430.1577843, 431.820487, 433.5611441,
    435.0195488, 436.1716363, 436.9889357, 437.5002032, 437.7869903,
    437.8766057, 437.8213491, 437.7274626, 437.7078866, 437.7788611,
    437.8445198, 437.8683068, 437.8703572, 437.859405, 437.853074,
    437.8949482, 438.0530494, 438.345312, 438.7162536, 439.1575488,
    439.6764605, 440.3074271, 441.1458819, 442.2338401, 443.4860781,
    444.7443925, 446.0355081, 447.4656652, 448.9376373, 450.3654743,
    451.7485113, 453.0942818, 454.439826, 455.864899, 457.3867801,
    458.9132059, 460.3168058, 461.5041933, 462.5335175, 463.4810505,
    464.3250305, 465.0548703, 465.6154622, 465.9270286, 466.0458211,
    466.1576256, 466.4147516, 466.8421265, 467.4728557, 468.2524625,
    469.1109809, 470.0840794, 471.1862141, 472.4444853, 473.8059477,
    475.1663277, 476.4613729, 477.6273048, 478.6385155, 479.5076241,
    480.3443233, 481.2673959, 482.1693811, 482.9523212, 483.7210283,
    484.4151801, 484.9033703, 485.359147, 485.9951315, 486.7393903,
    487.3373768, 487.6899059, 487.9398565, 488.1952628, 488.4803215,
    488.8787011, 489.422148, 490.0506159, 490.7181759, 491.4199564,
    492.2093079, 493.0584578, 493.8186942, 494.4622863, 495.0853066,
    495.7404024, 496.3390335, 496.7616166, 497.0154336, 497.1054916,
    497.0613642, 496.9361203, 496.68379, 496.329637, 495.9115805,
    495.3214273, 494.5384949, 493.6416471, 492.7049994, 491.7995236,
    490.9440033, 490.2262297, 489.7334614, 489.3784553, 489.0312823,
    488.6215641, 488.1171883, 487.5049831, 486.8669117, 486.2681649,
    485.6439154, 484.9656024, 484.2754416, 483.6158558, 482.9497434,
    482.2326787, 481.5012769, 480.7710758, 480.0378419, 479.366482,
    478.8636949, 478.5316245, 478.2985669, 478.1472076, 478.0460151,
    477.97178, 477.8135375, 477.4444904, 476.8837206, 476.1707624,
    475.305954, 474.2900386, 473.1441491, 471.8695659, 470.4639546,
    468.8853751, 467.241017, 465.7517735, 464.4208695, 463.1572668,
    461.9822925, 460.9038653, 459.8908486, 458.9677838, 458.134465,
    457.3953718, 456.7475377, 456.1415715, 455.5656166, 455.0475672,
    454.6342296, 454.3152035, 453.9668721, 453.5143923, 453.0513234,
    452.6803208, 452.331345, 451.8722566, 451.2845886, 450.6519342,
    450.0008844, 449.2487514, 448.3665152, 447.4439411, 446.5650751,
    445.6960573, 444.7948212, 443.8608426, 442.8821104, 441.8778847,
    440.9085097, 440.037799, 439.2690839, 438.5676971, 437.9270094,
    437.3270163, 436.7381402, 436.1846979, 435.6920217, 435.2251644,
    434.7495081, 434.2801587, 433.8305906, 433.3692367, 432.9134971,
    432.5201128, 432.1702163, 431.8723759, 431.6051239, 431.2946052,
    430.9256919, 430.5272735, 430.1621669, 429.8479431, 429.5551761,
    429.2817482, 429.0116012, 428.7323641, 428.4602092, 428.1539371,
    427.790381, 427.3786655, 426.8541266, 426.1688113, 425.3383357,
    424.3891937, 423.4152102, 422.479834, 421.5528266, 420.5981594,
    419.6329395, 418.7037289, 417.8358257, 417.0662417, 416.3930827,
    415.7686278, 415.0951856, 414.3051034, 413.4423345, 412.5911928,
    411.8098106, 411.047148, 410.2432741, 409.4444767, 408.6928123,
    407.9838791, 407.3699619, 406.9214602, 406.6219814, 406.3960829,
    406.2271025, 406.1210964, 406.0406477, 405.9748235, 405.9327884,
    405.9381116, 405.9514391, 405.9234769, 405.9261235, 405.9916165,
    406.06898, 406.1215176, 406.1393315, 406.1596405, 406.2004615,
    406.2185251, 406.2020512, 406.142051, 406.0072677, 405.8184974,
    405.5984761, 405.3704934, 405.1586462, 404.940593, 404.7103323,
    404.4753962, 404.2467094, 404.0152421, 403.771371, 403.5587716,
    403.365646, 403.1664709, 403.0029525, 402.9111914, 402.9006898,
    402.9543913, 403.0475134, 403.1835476, 403.3829257, 403.6238214,
    403.8615935, 404.1130103, 404.4055502, 404.7313816, 405.1083282,
    405.5818496, 406.1511542, 406.7632409, 407.3392327, 407.7739455,
    408.0470879, 408.250307, 408.4385333, 408.6159322, 408.7938943,
    408.9847311, 409.2395872, 409.5881781, 409.9705829, 410.3253319,
    410.6699129, 411.0378153, 411.3833967, 411.7186592, 412.1275774,
    412.6106308, 413.1438245, 413.7486245, 414.366279, 414.8852443,
    415.2506181, 415.4140917, 415.3691327, 415.2117745, 415.0381839,
    414.8189745, 414.4926095, 414.069545, 413.5729507, 413.0339316,
    412.5194512, 411.9909059, 411.3342614, 410.5417909, 409.6572722,
    408.7028966, 407.7679602, 406.9242196, 406.1369669, 405.3871517,
    404.6516079, 403.9291875, 403.2606497, 402.6145921, 401.9473658,
    401.3263469, 400.7947733, 400.3009684, 399.8341357, 399.4163874,
    399.0527222, 398.7375597, 398.4628624, 398.1898977, 397.87378,
    397.5213785
)


_IRRADIANCE_DATA = (
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 0.9,
    1.0, 1.0, 0.9, 0.9, 0.7, 0.4, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0
)


_TRIANGLE = (
    0.0, 0.09090909090909091, 0.18181818181818182, 0.2727272727272727,
    0.36363636363636365, 0.4545454545454546, 0.5454545454545454,
    0.6363636363636364, 0.7272727272727273, 0.8181818181818182,
    0.9090909090909092, 1.0, 1.0, 0.9090909090909092,
    0.8181818181818182, 0.7272727272727273, 0.6363636363636364,
    0.5454545454545454, 0.4545454545454546, 0.36363636363636365,
    0.2727272727272727, 0.18181818181818182, 0.09090909090909091, 0.0
)


@pytest.fixture(scope="session")
def model_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("grid_model")


@pytest.fixture(scope="session")
def grid_model_path(model_dir, irradiance_path, wind_path, triangle_path):
    grid_path = model_dir / "test_circuit.dss"
    with open(grid_path, 'w', newline='\n') as f:
        f.write(_SIMPLE_DSS)
    return grid_path


@pytest.fixture(scope="session")
def grid_definition():
    return _SIMPLE_DSS


@pytest.fixture(scope="session")
def triangle_data():
    return _TRIANGLE


@pytest.fixture(scope="session")
def triangle_path(model_dir, triangle_data):
    path = model_dir / "triangle.csv"
    with open(path, 'w', newline='\n') as f:
        f.write("\n".join(map(str, triangle_data)))
    return path


@pytest.fixture(scope="session")
def irradiance_data():
    return _IRRADIANCE_DATA


@pytest.fixture(scope="session")
def irradiance_path(model_dir, irradiance_data):
    path = model_dir / "irradiance.csv"
    with open(path, 'w', newline='\n') as f:
        f.write("\n".join(map(str, irradiance_data)))
    return path


@pytest.fixture(scope="session")
def wind_data():
    return _WIND_DATA


@pytest.fixture(scope="session")
def wind_path(model_dir, wind_data):
    path = model_dir / "zavwind.csv"
    with open(path, 'w', newline='\n') as f:
        f.write("\n".join(map(str, wind_data)))
    return path
