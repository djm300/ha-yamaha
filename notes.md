# Yamaha Zone Investigation

Date: 2026-03-09

Live receiver verification and repeatable manual test steps were moved to `livetesting.md`.

## What was wrong in `rxv`

- `RXV.zones()` only used `YNC_Tag` from `Func="Subunit"` menus.
- On this Yamaha XML, the Zone B menu has `Title_1="Zone B"` but still uses `YNC_Tag="Main_Zone"`.
- That made `rxv` discover `["Main_Zone", "Main_Zone"]` instead of `["Main_Zone", "Zone_B"]`.
- Zone B reads also used the wrong request wrapper. This model expects Zone B volume and mute under `Main_Zone`, for example `Main_Zone/Volume/Zone_B/...`.

## Power control findings

- Direct `Zone_B_Power` GET/PUT requests do not work on this receiver.
- The actual zone power control is exposed through speaker selection:
  - Zone 1 power maps to `Speaker_Preout/Speaker_AB/Speaker_A`
  - Zone 2 power maps to `Speaker_Preout/Speaker_AB/Speaker_B`
- The working requests match the Home Assistant shell commands you provided.
- Zone power state is visible in `Basic_Status` under:
  - `Main_Zone/Basic_Status/Speaker_Preout/Speaker_AB/Speaker_A`
  - `Main_Zone/Basic_Status/Speaker_Preout/Speaker_AB/Speaker_B`

## Routing findings

- `RXV.zone_controllers()` creates one controller object per discovered zone and sets a different default `zone` on each object.
- On this receiver, per-zone routing works for:
  - speaker enable/disable via `RXV.enabled`
  - volume via `RXV.volume`
  - mute via `RXV.mute`
- For `Zone_B`, source reads and writes are routed differently in code than `Main_Zone`:
  - `Main_Zone.input` uses the normal zone request wrapper
  - `Zone_B.input` uses a `Main_Zone` wrapper
- Despite that different XML routing, this receiver behaves as if source selection is shared with the main zone rather than independently switchable per zone.

## Code changes made

- Zone discovery now maps `Title_1="Zone B"` to `Zone_B`.
- Zone B input, volume, and mute use the correct `Main_Zone` wrapper.
- `RXV.on` remains receiver power for all zones.
- `RXV.enabled` is the per-zone switch:
  - `Main_Zone.enabled` uses `Speaker_A`
  - `Zone_B.enabled` uses `Speaker_B`
- `RXV.input` uses different XML for `Zone_B` than for `Main_Zone`, but the receiver still behaves as a shared-source device.
- `basic_status.on` remains receiver power (`Power_Control/Power`).
- Regression tests were added for:
  - Zone B discovery
  - Zone B request formatting
  - Zone B `enabled` writes using `Speaker_B`

## Validation

- `python3 -m py_compile rxv/rxv.py tests/test_rxv.py` passed.
- Full `pytest` was not runnable in this environment because `requests_mock` is not installed.

Observed behavior:

```python
zone1_up_1
  before = -500
  after = -490

zone1_down_1
  before = -490
  after = -500

zone1_up_5
  before = -500
  after = -450

zone1_down_5
  before = -450
  after = -500

zone2_up_1
  before = -700
  after = -690

zone2_down_1
  before = -690
  after = -700

zone2_up_5
  before = -700
  after = -650

zone2_down_5
  before = -650
  after = -700
```

Verified command forms:

```sh
# Zone 1 relative volume
<YAMAHA_AV cmd="PUT"><Main_Zone><Volume><Lvl><Val>Up 1 dB</Val><Exp></Exp><Unit></Unit></Lvl></Volume></Main_Zone></YAMAHA_AV>
<YAMAHA_AV cmd="PUT"><Main_Zone><Volume><Lvl><Val>Down 1 dB</Val><Exp></Exp><Unit></Unit></Lvl></Volume></Main_Zone></YAMAHA_AV>
<YAMAHA_AV cmd="PUT"><Main_Zone><Volume><Lvl><Val>Up 5 dB</Val><Exp></Exp><Unit></Unit></Lvl></Volume></Main_Zone></YAMAHA_AV>
<YAMAHA_AV cmd="PUT"><Main_Zone><Volume><Lvl><Val>Down 5 dB</Val><Exp></Exp><Unit></Unit></Lvl></Volume></Main_Zone></YAMAHA_AV>

# Zone 2 relative volume
<YAMAHA_AV cmd="PUT"><Main_Zone><Volume><Zone_B><Lvl><Val>Up 1 dB</Val><Exp></Exp><Unit></Unit></Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>
<YAMAHA_AV cmd="PUT"><Main_Zone><Volume><Zone_B><Lvl><Val>Down 1 dB</Val><Exp></Exp><Unit></Unit></Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>
<YAMAHA_AV cmd="PUT"><Main_Zone><Volume><Zone_B><Lvl><Val>Up 5 dB</Val><Exp></Exp><Unit></Unit></Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>
<YAMAHA_AV cmd="PUT"><Main_Zone><Volume><Zone_B><Lvl><Val>Down 5 dB</Val><Exp></Exp><Unit></Unit></Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>
```
