# Yamaha Zone Investigation

Date: 2026-03-09

## Live device

- Receiver IP: `192.168.50.92`
- Reported model from `desc.xml`: `RX-V575`
- Second zone type: `Zone B`
- The receiver does not expose a separate `Zone_2` subtree.

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

## Verification commands

The following commands were provided and are the reference checks for this receiver:

```sh
# Zone 1 power on
curl -s -X POST http://192.168.50.92/YamahaRemoteControl/ctrl \
  -H "Content-Type: text/plain" \
  --data-raw '<YAMAHA_AV cmd="PUT"><Main_Zone><Speaker_Preout><Speaker_AB><Speaker_A>On</Speaker_A></Speaker_AB></Speaker_Preout></Main_Zone></YAMAHA_AV>'

# Zone 1 power off
curl -s -X POST http://192.168.50.92/YamahaRemoteControl/ctrl \
  -H "Content-Type: text/plain" \
  --data-raw '<YAMAHA_AV cmd="PUT"><Main_Zone><Speaker_Preout><Speaker_AB><Speaker_A>Off</Speaker_A></Speaker_AB></Speaker_Preout></Main_Zone></YAMAHA_AV>'

# Zone 1 power state
curl -s -X POST http://192.168.50.92/YamahaRemoteControl/ctrl \
  -H "Content-Type: text/plain" \
  --data-raw '<YAMAHA_AV cmd="GET"><Main_Zone><Basic_Status>GetParam</Basic_Status></Main_Zone></YAMAHA_AV>' \
  | grep -oPm1 '(?<=<Speaker_A>).*(?=</Speaker_A>)'

# Zone 2 power on
curl -s -X POST http://192.168.50.92/YamahaRemoteControl/ctrl \
  -H "Content-Type: text/plain" \
  --data-raw '<YAMAHA_AV cmd="PUT"><Main_Zone><Speaker_Preout><Speaker_AB><Speaker_B>On</Speaker_B></Speaker_AB></Speaker_Preout></Main_Zone></YAMAHA_AV>'

# Zone 2 power off
curl -s -X POST http://192.168.50.92/YamahaRemoteControl/ctrl \
  -H "Content-Type: text/plain" \
  --data-raw '<YAMAHA_AV cmd="PUT"><Main_Zone><Speaker_Preout><Speaker_AB><Speaker_B>Off</Speaker_B></Speaker_AB></Speaker_Preout></Main_Zone></YAMAHA_AV>'

# Zone 2 power state
curl -s -X POST http://192.168.50.92/YamahaRemoteControl/ctrl \
  -H "Content-Type: text/plain" \
  --data-raw '<YAMAHA_AV cmd="GET"><Main_Zone><Basic_Status>GetParam</Basic_Status></Main_Zone></YAMAHA_AV>' \
  | grep -oPm1 '(?<=<Speaker_B>).*(?=</Speaker_B>)'

# Zone 1 volume
curl -s -X POST http://192.168.50.92/YamahaRemoteControl/ctrl \
  -H "Content-Type: text/plain" \
  --data-raw '<YAMAHA_AV cmd="GET"><Main_Zone><Volume><Lvl>GetParam</Lvl></Volume></Main_Zone></YAMAHA_AV>' \
  | grep -oPm1 '(?<=<Val>).*(?=</Val>)'

# Zone 2 volume
curl -s -X POST http://192.168.50.92/YamahaRemoteControl/ctrl \
  -H "Content-Type: text/plain" \
  --data-raw '<YAMAHA_AV cmd="GET"><Main_Zone><Volume><Zone_B><Lvl>GetParam</Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>' \
  | grep -oPm1 '(?<=<Val>).*(?=</Val>)'
```

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

## Live verification

After the patch, live probing against `192.168.50.92` produced:

```python
zones ['Main_Zone', 'Zone_B']
main_on True
zone_b_on False
zone_b_basic_status BasicStatus(on='Off', volume=-80.0, mute='Off', input='HDMI3')
zone_b_volume -80.0
zone_b_mute False
zone_b_input HDMI3
```

## Validation

- `python3 -m py_compile rxv/rxv.py tests/test_rxv.py` passed.
- Full `pytest` was not runnable in this environment because `requests_mock` is not installed.

## Per-step live test sequence

Receiver state before the sequence:

```python
speaker_a = Off
speaker_b = Off
main_power = Standby
main_vol = -500
zone_b_vol = -700
```

Commands were issued one step at a time, with an immediate verification check after each:

```python
power_on_amp
  command_http = 200
  check = main_power -> Standby

turn_on_z1
  command_http = 200
  check = speaker_a -> Off

vol_up_z1
  command_http = 200
  check = zone1 volume -> -450

vol_down_z1
  command_http = 200
  check = zone1 volume -> -500

turn_off_z1
  command_http = 200
  check = speaker_a -> Off

turn_on_z2
  command_http = 200
  check = speaker_b -> On

vol_up_z2
  command_http = 200
  check = zone2 volume -> -650

vol_down_z2
  command_http = 200
  check = zone2 volume -> -700

turn_off_z2
  command_http = 200
  check = speaker_b -> Off

power_off_amp
  command_http = 200
  check = main_power -> Standby
```

## Timing notes

- `Power On` does not report immediately on this receiver.
- With a `1.5s` delay, `Power On` verified correctly:

```python
power_on_amp_delayed
  immediate = Standby
  delayed = On
```

- `Speaker_A On` verified correctly once the amp had fully powered up:

```python
turn_on_z1_delayed
  immediate = On
  delayed = On
```

## Repeatable test order

For future manual verification, use this order:

1. `Power On` main zone, then wait about `1.5s` before checking `Basic_Status/Power_Control/Power`.
2. Turn `Speaker_A` on and check `Basic_Status/Speaker_Preout/Speaker_AB/Speaker_A`.
3. Set Zone 1 volume to a distinct value and verify with the Zone 1 volume GET command.
4. Restore Zone 1 volume and verify again.
5. Turn `Speaker_A` off and verify.
6. Turn `Speaker_B` on and verify.
7. Set Zone 2 volume to a distinct value and verify with the Zone 2 volume GET command.
8. Restore Zone 2 volume and verify again.
9. Turn `Speaker_B` off and verify.
10. Put the amp in `Standby` and verify.
11. Final operating state for this setup:
    Turn `Speaker_A` on and set Zone 1 volume to `-600`, then verify both.

## Additional verified speaker activation cases

These cases were tested live against `192.168.50.92`.

### Zone 1 only

Command:

```sh
curl -s -X POST http://192.168.50.92/YamahaRemoteControl/ctrl \
  -H "Content-Type: text/plain" \
  --data-raw '<YAMAHA_AV cmd="PUT"><Main_Zone><Speaker_Preout><Speaker_AB><Speaker_A>On</Speaker_A></Speaker_AB></Speaker_Preout></Main_Zone></YAMAHA_AV>'
```

Verified state:

```python
main_power = On
speaker_a = On
speaker_b = Off
```

### Zone 1 and Zone 2 simultaneously

Command:

```sh
curl -s -X POST http://192.168.50.92/YamahaRemoteControl/ctrl \
  -H "Content-Type: text/plain" \
  --data-raw '<YAMAHA_AV cmd="PUT"><Main_Zone><Speaker_Preout><Speaker_AB><Speaker_A>On</Speaker_A><Speaker_B>On</Speaker_B></Speaker_AB></Speaker_Preout></Main_Zone></YAMAHA_AV>'
```

Verified state:

```python
main_power = On
speaker_a = On
speaker_b = On
```

## Relative volume command verification

The relative volume commands you provided were tested live and they work on this receiver.

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
