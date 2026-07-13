# Round-1 candidate campaign - raw vs Lupine-corrected

Generated: 2026-07-13T14:14:06.554750+00:00 | models: chgnet, mace-mp-small, mace-mp-medium, mace-mpa-0-medium

Bias arm: biases from C:/Users/alexw/Downloads/lupine-rhizo/data/candidates/model_biases.v1.json (schema lupine.model_biases.v1); cij available: False

## Concordance thresholds

| property | flag | refuse | baseline n |
|---|---|---|---|
| a0 | 0.0060 | 0.0086 | 21 |
| b0 | 0.2490 | 0.3848 | 21 |
| c11 | 0.4885 | 1.2107 | 21 |
| c12 | 0.5704 | 1.0590 | 21 |
| c44 | 1.2221 | 3.7892 | 21 |

## hea-cocrni - **CERTIFIED**

group: hea-fcc | structure: fcc-rss | formula: CoCrNi | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 3.5600 | 3.5207 | 3.5258 | 3.5237 | 3.5339 | 3.5168 | 3.5163 | 3.5182 | 3.5258 | PASS |
| b0 | 189.0000 | 211.0230 | 200.6867 | 201.2098 | 197.0728 | 246.3934 | 201.7839 | 235.9995 | 218.4673 | PASS |
| c11 | 249.0000 | 238.1820 | 237.1219 | 238.6779 | 264.6861 | 238.1820 (uncorr) | 237.1219 (uncorr) | 238.6779 (uncorr) | 264.6861 (uncorr) | PASS |
| c12 | 159.0000 | 174.8108 | 175.7058 | 177.3767 | 154.1445 | 174.8108 (uncorr) | 175.7058 (uncorr) | 177.3767 (uncorr) | 154.1445 (uncorr) | PASS |
| c44 | 138.0000 | 93.5647 | 95.5356 | 92.6121 | 127.4981 | 93.5647 (uncorr) | 95.5356 (uncorr) | 92.6121 (uncorr) | 127.4981 (uncorr) | PASS |

dynamic_return: PASS (dE=-6.06e-05 eV/atom, max disp=0.023 A, 108 atoms)

## hea-cocrfeni - **FLAGGED**

group: hea-fcc | structure: fcc-rss | formula: CoCrFeNi | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 3.5700 | 3.5249 | 3.5386 | 3.5372 | 3.5550 | 3.5210 | 3.5291 | 3.5317 | 3.5469 | FLAG |
| b0 | 163.0000 | 155.2552 | 191.5907 | 182.8553 | 168.0128 | 181.2782 | 192.6382 | 214.4715 | 186.2525 | PASS |
| c11 | - | 158.4237 | 219.7083 | 212.9839 | 207.3107 | 158.4237 (uncorr) | 219.7083 (uncorr) | 212.9839 (uncorr) | 207.3107 (uncorr) | PASS |
| c12 | - | 123.8198 | 164.3083 | 157.9057 | 137.5384 | 123.8198 (uncorr) | 164.3083 (uncorr) | 157.9057 (uncorr) | 137.5384 (uncorr) | PASS |
| c44 | - | 73.6128 | 96.0917 | 98.1471 | 120.0047 | 73.6128 (uncorr) | 96.0917 (uncorr) | 98.1471 (uncorr) | 120.0047 (uncorr) | PASS |

dynamic_return: PASS (dE=-1.19e-04 eV/atom, max disp=0.025 A, 108 atoms)

## hea-coni - **FLAGGED**

group: hea-fcc | structure: fcc-rss | formula: CoNi | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 3.5350 | 3.5091 | 3.5102 | 3.5095 | 3.5254 | 3.5052 | 3.5009 | 3.5041 | 3.5173 | PASS |
| b0 | 172.0000 | 166.8728 | 175.4124 | 205.3256 | 216.2435 | 194.8431 | 176.3714 | 240.8269 | 239.7192 | FLAG |
| c11 | - | 196.1945 | 239.1853 | 266.8644 | 315.8230 | 196.1945 (uncorr) | 239.1853 (uncorr) | 266.8644 (uncorr) | 315.8230 (uncorr) | PASS |
| c12 | - | 139.3235 | 139.3290 | 172.3201 | 165.3933 | 139.3235 (uncorr) | 139.3290 (uncorr) | 172.3201 (uncorr) | 165.3933 (uncorr) | PASS |
| c44 | - | 90.9963 | 136.2582 | 117.3378 | 145.9420 | 90.9963 (uncorr) | 136.2582 (uncorr) | 117.3378 (uncorr) | 145.9420 (uncorr) | PASS |

dynamic_return: PASS (dE=-2.49e-06 eV/atom, max disp=0.015 A, 108 atoms)

## hea-feni - **REFUSED**

group: hea-fcc | structure: fcc-rss | formula: FeNi | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 3.5820 | 3.5485 | 3.5535 | 3.5484 | 3.5817 | 3.5446 | 3.5440 | 3.5429 | 3.5735 | REFUSE |
| b0 | 176.7000 | 108.7322 | 143.0690 | 148.6368 | 171.9603 | 126.9572 | 143.8512 | 174.3365 | 190.6286 | REFUSE |
| c11 | - | 122.3605 | 168.3440 | 185.4693 | 218.8044 | 122.3605 (uncorr) | 168.3440 (uncorr) | 185.4693 (uncorr) | 218.8044 (uncorr) | FLAG |
| c12 | - | 100.4201 | 113.4587 | 124.5789 | 148.2746 | 100.4201 (uncorr) | 113.4587 (uncorr) | 124.5789 (uncorr) | 148.2746 (uncorr) | PASS |
| c44 | - | 61.6958 | 89.9989 | 98.7138 | 111.1762 | 61.6958 (uncorr) | 89.9989 (uncorr) | 98.7138 (uncorr) | 111.1762 (uncorr) | PASS |

dynamic_return: PASS (dE=-6.65e-05 eV/atom, max disp=0.019 A, 108 atoms)

## hp-cssncl3 - **FLAGGED**

group: halide-perovskite | structure: perovskite | formula: CsSnCl3 | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 5.5790 | 5.6611 | 5.6129 | 5.6365 | 5.6263 | 5.6548 | 5.6108 | 5.6307 | 5.6172 | FLAG |
| b0 | 22.7000 | 20.7880 | 29.5565 | 25.3656 | 21.9277 | 22.5125 | 29.5310 | 25.0742 | 22.0581 | FLAG |
| c11 | 50.6600 | 31.5129 | 70.6928 | 59.8849 | 48.3530 | 31.5129 (uncorr) | 70.6928 (uncorr) | 59.8849 (uncorr) | 48.3530 (uncorr) | FLAG |
| c12 | 8.7100 | 10.2829 | 9.1936 | 8.2184 | 8.8959 | 10.2829 (uncorr) | 9.1936 (uncorr) | 8.2184 (uncorr) | 8.8959 (uncorr) | PASS |
| c44 | 6.0100 | 0.6558 | 6.7170 | 4.6325 | 7.4849 | 0.6558 (uncorr) | 6.7170 (uncorr) | 4.6325 (uncorr) | 7.4849 (uncorr) | PASS |

dynamic_return: PASS (dE=-1.58e-03 eV/atom, max disp=0.172 A, 5 atoms)

## hp-cssnbr3 - **REFUSED**

group: halide-perovskite | structure: perovskite | formula: CsSnBr3 | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 5.8040 | 5.9216 | 5.8745 | 5.8948 | 5.8848 | 5.9151 | 5.8724 | 5.8887 | 5.8753 | FLAG |
| b0 | 19.0900 | 16.4806 | 20.5358 | 17.2626 | 18.8071 | 17.8478 | 20.5180 | 17.0643 | 18.9190 | PASS |
| c11 | 43.8900 | 24.6681 | 51.3297 | 44.3750 | 41.5045 | 24.6681 (uncorr) | 51.3297 (uncorr) | 44.3750 (uncorr) | 41.5045 (uncorr) | FLAG |
| c12 | 6.6900 | 15.1050 | 5.1438 | 3.5971 | 7.4493 | 15.1050 (uncorr) | 5.1438 (uncorr) | 3.5971 (uncorr) | 7.4493 (uncorr) | REFUSE |
| c44 | 5.2100 | 0.3811 | 5.0657 | 3.8895 | 6.0809 | 0.3811 (uncorr) | 5.0657 (uncorr) | 3.8895 (uncorr) | 6.0809 (uncorr) | FLAG |

dynamic_return: PASS (dE=1.81e-04 eV/atom, max disp=0.107 A, 5 atoms)

## hp-cssni3 - **REFUSED**

group: halide-perovskite | structure: perovskite | formula: CsSnI3 | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 6.2190 | 6.3308 | 6.2711 | 6.2818 | 6.2863 | 6.3237 | 6.2688 | 6.2753 | 6.2762 | REFUSE |
| b0 | 17.5900 | 11.1858 | 15.5396 | 16.6727 | 16.2175 | 12.1138 | 15.5261 | 16.4811 | 16.3139 | FLAG |
| c11 | 21.3400 | 10.3791 | 34.9822 | 37.3778 | 35.7290 | 10.3791 (uncorr) | 34.9822 (uncorr) | 37.3778 (uncorr) | 35.7290 (uncorr) | FLAG |
| c12 | 1.2200 | 4.4088 | 5.6889 | 6.1977 | 6.5209 | 4.4088 (uncorr) | 5.6889 (uncorr) | 6.1977 (uncorr) | 6.5209 (uncorr) | PASS |
| c44 | 5.7400 | 0.1461 | 4.0953 | 3.4221 | 4.2733 | 0.1461 (uncorr) | 4.0953 (uncorr) | 3.4221 (uncorr) | 4.2733 (uncorr) | PASS |

dynamic_return: PASS (dE=3.68e-04 eV/atom, max disp=0.098 A, 5 atoms)

## hp-csgei3 - **REFUSED**

group: halide-perovskite | structure: perovskite | formula: CsGeI3 | Born aggregate: PASS

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | - | 6.0194 | 5.9485 | 6.0242 | 6.0252 | 6.0127 | 5.9464 | 6.0181 | 6.0156 | REFUSE |
| b0 | 18.8900 | 18.3552 | 17.7299 | 16.7738 | 19.1142 | 19.8779 | 17.7146 | 16.5811 | 19.2279 | PASS |
| c11 | 40.3200 | 26.8054 | 46.9567 | 36.9558 | 40.5792 | 26.8054 (uncorr) | 46.9567 (uncorr) | 36.9558 (uncorr) | 40.5792 (uncorr) | FLAG |
| c12 | 8.1800 | 18.8086 | 3.0470 | 6.5417 | 8.3704 | 18.8086 (uncorr) | 3.0470 (uncorr) | 6.5417 (uncorr) | 8.3704 (uncorr) | REFUSE |
| c44 | 8.8700 | 4.2032 | 8.5719 | 6.0996 | 8.0151 | 4.2032 (uncorr) | 8.5719 (uncorr) | 6.0996 (uncorr) | 8.0151 (uncorr) | PASS |

dynamic_return: PASS (dE=-1.64e-03 eV/atom, max disp=0.177 A, 5 atoms)

## hp-cspbi3-control - **REFUSED**

group: halide-perovskite | structure: perovskite | formula: CsPbI3 | Born aggregate: FAIL

| property | reference | chgnet raw | mace-mp-small raw | mace-mp-medium raw | mace-mpa-0-medium raw | chgnet corr | mace-mp-small corr | mace-mp-medium corr | mace-mpa-0-medium corr | concordance |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | 6.2894 | 6.4102 | 6.3792 | 6.3900 | 6.4098 | 6.4030 | 6.3769 | 6.3834 | 6.3995 | PASS |
| b0 | 14.7600 | 15.2008 | 15.3575 | 17.5936 | 15.9538 | 16.4619 | 15.3442 | 17.3915 | 16.0486 | PASS |
| c11 | 34.8400 | 21.2577 | 36.6633 | 38.1487 | 36.1649 | 21.2577 (uncorr) | 36.6633 (uncorr) | 38.1487 (uncorr) | 36.1649 (uncorr) | PASS |
| c12 | 4.7300 | 9.3282 | 4.6217 | 7.2601 | 5.9525 | 9.3282 (uncorr) | 4.6217 (uncorr) | 7.2601 (uncorr) | 5.9525 (uncorr) | FLAG |
| c44 | 3.6600 | -1.5419 | 3.1984 | 3.5357 | 3.9448 | -1.5419 (uncorr) | 3.1984 (uncorr) | 3.5357 (uncorr) | 3.9448 (uncorr) | FLAG |

dynamic_return: PASS (dE=3.07e-04 eV/atom, max disp=0.087 A, 5 atoms)

## Arm metrics: |relative error| vs references (raw vs corrected)

| group | property | n cells | median raw | median corr | mean raw | mean corr |
|---|---|---|---|---|---|---|
| all | a0 | 32 | 0.99% | 1.08% | 1.07% | 1.11% |
| all | b0 | 36 | 7.95% | 10.91% | 10.97% | 13.82% |
| all | c11 | 24 | 12.98% | 12.98% | 23.39% | 23.39% |
| all | c12 | 24 | 21.57% | 21.57% | 89.04% | 89.04% |
| all | c44 | 24 | 25.45% | 25.45% | 35.17% | 35.17% |
| halide-perovskite | a0 | 16 | 1.41% | 1.29% | 1.36% | 1.25% |
| halide-perovskite | b0 | 20 | 7.95% | 7.37% | 10.14% | 9.68% |
| halide-perovskite | c11 | 20 | 17.58% | 17.58% | 27.09% | 27.09% |
| halide-perovskite | c12 | 20 | 36.04% | 36.04% | 105.10% | 105.10% |
| halide-perovskite | c44 | 20 | 24.94% | 24.94% | 37.03% | 37.03% |
| hea-fcc | a0 | 16 | 0.84% | 1.05% | 0.78% | 0.96% |
| hea-fcc | b0 | 16 | 9.06% | 16.89% | 12.02% | 19.00% |
| hea-fcc | c11 | 4 | 4.56% | 4.56% | 4.89% | 4.89% |
| hea-fcc | c12 | 4 | 10.23% | 10.23% | 8.77% | 8.77% |
| hea-fcc | c44 | 4 | 31.49% | 31.49% | 25.87% | 25.87% |

## Risk-coverage

- candidates: 9
- certified: 1, flagged: 3, refused: 5
- issued (certified+flagged): 4 (44% coverage)
