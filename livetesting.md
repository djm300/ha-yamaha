# Yamaha Live Testing

Date: 2026-03-09

## Live device

- Receiver IP: `192.168.50.92`
- Reported model from `desc.xml`: `RX-V575`
- Second zone type: `Zone B`
- The receiver does not expose a separate `Zone_2` subtree.

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
