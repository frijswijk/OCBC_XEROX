# Anchor Decision Diff Report (2026-02-24 18:33)

Feature flag: `XEROX_ENABLE_CROSS_DOCFORMAT_Y=1`

## CASIO
- Source DFA: `C:\ISIS\samples_pdd\OCBC\TEST_CASIO_CROSS\docdef\CASIO.dfa`
- Docformats tagged: 26
- Class counts: absolute=3, reset=1, carry=22
- First OUTLINE POSITION LEFT counts: LEFT NEXT=1, LEFT SAME=1, LEFT (FLOW_Y)=16, OTHER=8

## SIBS_CAST
- Source DFA: `C:\ISIS\samples_pdd\OCBC\TEST_SIBS_CROSS\docdef\SIBS_CAST.dfa`
- Docformats tagged: 11
- Class counts: absolute=2, reset=0, carry=9
- First OUTLINE POSITION LEFT counts: LEFT NEXT=0, LEFT SAME=0, LEFT (FLOW_Y)=6, OTHER=5

## Common Prefixes (CASIO vs SIBS_CAST)
| DOCFORMAT | CASIO | SIBS_CAST |
|---|---|---|
| DF_1 | carry / (none) | absolute / (none) |

## CASIO Decisions
| DOCFORMAT | Class | First POSITION LEFT |
|---|---|---|
| DF_MR | absolute | (none) |
| DF_A0 | carry | (none) |
| DF_YA | carry | (none) |
| DF_Y0 | carry | POSITION LEFT (FLOW_Y) |
| DF_Y1 | reset | POSITION LEFT SAME |
| DF_Y2 | carry | (none) |
| DF_B0 | carry | POSITION LEFT (FLOW_Y) |
| DF_C0 | carry | POSITION LEFT (FLOW_Y) |
| DF_M0 | carry | POSITION LEFT (FLOW_Y) |
| DF_T1 | carry | (none) |
| DF_M1 | carry | POSITION LEFT (FLOW_Y) |
| DF_D0 | carry | POSITION LEFT (FLOW_Y) |
| DF_D1 | carry | (none) |
| DF_M2 | absolute | POSITION LEFT NEXT |
| DF_E0 | carry | POSITION LEFT (FLOW_Y) |
| DF_E1 | carry | POSITION LEFT (FLOW_Y) |
| DF_E2 | carry | POSITION LEFT (FLOW_Y) |
| DF_E3 | carry | POSITION LEFT (FLOW_Y) |
| DF_M3 | carry | POSITION LEFT (FLOW_Y) |
| DF_T2 | absolute | (none) |
| DF_I1 | carry | POSITION LEFT (FLOW_Y) |
| DF_S1 | carry | POSITION LEFT (FLOW_Y) |
| DF_R1 | carry | POSITION LEFT (FLOW_Y) |
| DF_V1 | carry | POSITION LEFT (FLOW_Y) |
| DF_M4 | carry | POSITION LEFT (FLOW_Y) |
| DF_1 | carry | (none) |

## SIBS_CAST Decisions
| DOCFORMAT | Class | First POSITION LEFT |
|---|---|---|
| DF_STMTTP | absolute | (none) |
| DF_HEADER | carry | (none) |
| DF_MKTMSG | carry | (none) |
| DF_TRXHDR | carry | (none) |
| DF_CCASTB | carry | POSITION LEFT (FLOW_Y) |
| DF_ICASTB | carry | POSITION LEFT (FLOW_Y) |
| DF_CCASTX | carry | POSITION LEFT (FLOW_Y) |
| DF_ICASTX | carry | POSITION LEFT (FLOW_Y) |
| DF_CCASTS | carry | POSITION LEFT (FLOW_Y) |
| DF_ICASTS | carry | POSITION LEFT (FLOW_Y) |
| DF_1 | absolute | (none) |
