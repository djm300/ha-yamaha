from io import open

import requests_mock
import unittest

import rxv

FAKE_IP = '10.0.0.0'
DESC_XML = 'http://%s/YamahaRemoteControl/desc.xml' % FAKE_IP
CTRL_URL = 'http://%s/YamahaRemoteControl/ctrl' % FAKE_IP


def sample_content(name):
    with open('tests/samples/%s' % name, encoding='utf-8') as f:
        return f.read()


class TestRXV(unittest.TestCase):

    @requests_mock.mock()
    def test_basic_object(self, m):
        m.get(DESC_XML, text=sample_content('rx-v675-desc.xml'))
        rec = rxv.RXV(CTRL_URL)
        self.assertEqual(
            rec.unit_desc_url,
            'http://%s/YamahaRemoteControl/desc.xml' % FAKE_IP)


class TestDesc(unittest.TestCase):

    @requests_mock.mock()
    def test_discover_zones(self, m):
        m.get(DESC_XML, text=sample_content('rx-v675-desc.xml'))
        rec = rxv.RXV(CTRL_URL)
        zones = rec.zone_controllers()
        self.assertEqual(len(zones), 2, zones)
        self.assertEqual(zones[0].zone, "Main_Zone")
        self.assertEqual(zones[1].zone, "Zone_2")

    @requests_mock.mock()
    def test_discover_zone_b(self, m):
        m.get(DESC_XML, text=sample_content('rx-v579-desc.xml'))
        rec = rxv.RXV(CTRL_URL)
        zones = rec.zone_controllers()
        self.assertEqual(len(zones), 2, zones)
        self.assertEqual(zones[0].zone, "Main_Zone")
        self.assertEqual(zones[1].zone, "Zone_B")


class TestZoneB(unittest.TestCase):

    ZONE_B_BASIC_STATUS = (
        '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Basic_Status>'
        '<Power_Control><Power>On</Power></Power_Control><Volume><Lvl><Val>-510</Val><Exp>1</Exp><Unit>dB</Unit></Lvl>'
        '<Mute>Off</Mute><Zone_B><Lvl><Val>-405</Val><Exp>1</Exp><Unit>dB</Unit></Lvl>'
        '<Mute>On</Mute></Zone_B></Volume><Input><Input_Sel>AV4</Input_Sel></Input>'
        '<Speaker_Preout><Speaker_AB><Speaker_A>On</Speaker_A><Speaker_B>Off</Speaker_B></Speaker_AB></Speaker_Preout>'
        '</Basic_Status></Main_Zone></YAMAHA_AV>'
    )

    ZONE_B_POWER_STATUS = (
        '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Basic_Status><Speaker_Preout><Speaker_AB>'
        '<Speaker_A>On</Speaker_A><Speaker_B>On</Speaker_B></Speaker_AB></Speaker_Preout>'
        '</Basic_Status></Main_Zone></YAMAHA_AV>'
    )

    ZONE_B_VOLUME_STATUS = (
        '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Volume><Zone_B><Lvl><Val>-405</Val>'
        '<Exp>1</Exp><Unit>dB</Unit></Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>'
    )

    ZONE_B_MUTE_STATUS = (
        '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Volume><Zone_B><Mute>On</Mute>'
        '</Zone_B></Volume></Main_Zone></YAMAHA_AV>'
    )

    ZONE_B_INPUT_STATUS = (
        '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Input><Input_Sel>AV4</Input_Sel>'
        '</Input></Main_Zone></YAMAHA_AV>'
    )

    @requests_mock.mock()
    def test_zone_b_requests_use_main_zone_wrapper(self, m):
        m.get(DESC_XML, text=sample_content('rx-v579-desc.xml'))
        m.post(CTRL_URL, [
            {'text': self.ZONE_B_BASIC_STATUS},
            {'text': self.ZONE_B_POWER_STATUS},
            {'text': self.ZONE_B_VOLUME_STATUS},
            {'text': self.ZONE_B_MUTE_STATUS},
            {'text': self.ZONE_B_INPUT_STATUS},
        ])

        rec = rxv.RXV(CTRL_URL)
        rec.zone = "Zone_B"

        status = rec.basic_status
        self.assertEqual(status.on, 'On')
        self.assertEqual(status.volume, -40.5)

        self.assertTrue(rec.enabled)

        self.assertEqual(rec.volume, -40.5)

        self.assertTrue(rec.mute)

        self.assertEqual(rec.input, 'AV4')

    @requests_mock.mock()
    def test_zone_b_power_write_uses_speaker_b(self, m):
        m.get(DESC_XML, text=sample_content('rx-v579-desc.xml'))
        m.post(CTRL_URL, text='<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Speaker_Preout><Speaker_AB><Speaker_B /></Speaker_AB></Speaker_Preout></Main_Zone></YAMAHA_AV>')

        rec = rxv.RXV(CTRL_URL)
        rec.zone = "Zone_B"
        rec.enabled = True


class TestReceiverScenarios(unittest.TestCase):

    @staticmethod
    def _basic_status_xml(power="Standby", speaker_a="Off", speaker_b="Off",
                          main_vol="-500", zone_b_vol="-700",
                          mute="Off", zone_b_mute="Off", input_sel="HDMI3"):
        return (
            '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Basic_Status>'
            f'<Power_Control><Power>{power}</Power></Power_Control>'
            f'<Volume><Lvl><Val>{main_vol}</Val><Exp>1</Exp><Unit>dB</Unit></Lvl>'
            f'<Mute>{mute}</Mute><Zone_B><Lvl><Val>{zone_b_vol}</Val><Exp>1</Exp>'
            f'<Unit>dB</Unit></Lvl><Mute>{zone_b_mute}</Mute></Zone_B></Volume>'
            f'<Input><Input_Sel>{input_sel}</Input_Sel></Input>'
            '<Speaker_Preout><Speaker_AB>'
            f'<Speaker_A>{speaker_a}</Speaker_A><Speaker_B>{speaker_b}</Speaker_B>'
            '</Speaker_AB></Speaker_Preout>'
            '</Basic_Status></Main_Zone></YAMAHA_AV>'
        )

    @staticmethod
    def _zone_b_volume_xml(value):
        return (
            '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Volume><Zone_B><Lvl>'
            f'<Val>{value}</Val><Exp>1</Exp><Unit>dB</Unit>'
            '</Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>'
        )

    @staticmethod
    def _main_volume_xml(value):
        return (
            '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Volume><Lvl>'
            f'<Val>{value}</Val><Exp>1</Exp><Unit>dB</Unit>'
            '</Lvl></Volume></Main_Zone></YAMAHA_AV>'
        )

    @requests_mock.mock()
    def test_main_zone_power_uses_power_control(self, m):
        m.get(DESC_XML, text=sample_content('rx-v579-desc.xml'))
        m.post(CTRL_URL, [
            {'text': '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Power_Control><Power>On</Power></Power_Control></Main_Zone></YAMAHA_AV>'},
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Power_Control><Power></Power></Power_Control></Main_Zone></YAMAHA_AV>'},
            {'text': '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Power_Control><Power>Standby</Power></Power_Control></Main_Zone></YAMAHA_AV>'},
        ])

        rec = rxv.RXV(CTRL_URL)
        self.assertTrue(rec.on)
        rec.on = False
        self.assertFalse(rec.on)

    @requests_mock.mock()
    def test_zone1_only_speaker_state(self, m):
        m.get(DESC_XML, text=sample_content('rx-v579-desc.xml'))
        m.post(CTRL_URL, text=self._basic_status_xml(power="On", speaker_a="On", speaker_b="Off"))

        rec = rxv.RXV(CTRL_URL)
        status = rec.basic_status
        self.assertEqual(status.on, "On")
        self.assertTrue(rec.enabled)
        self.assertFalse(rec.zone_controllers()[1].enabled)

    @requests_mock.mock()
    def test_zone1_and_zone2_simultaneous_speaker_command(self, m):
        m.get(DESC_XML, text=sample_content('rx-v579-desc.xml'))
        m.post(CTRL_URL, [
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Speaker_Preout><Speaker_AB></Speaker_AB></Speaker_Preout></Main_Zone></YAMAHA_AV>'},
            {'text': self._basic_status_xml(power="On", speaker_a="On", speaker_b="On")},
        ])

        rec = rxv.RXV(CTRL_URL)
        request = rxv.rxv.SpeakerControl.format(speaker="Speaker_A", state="On").replace(
            '</Speaker_AB></Speaker_Preout>',
            '<Speaker_B>On</Speaker_B></Speaker_AB></Speaker_Preout>'
        )
        rec._main_zone_request('PUT', request)
        response = rec._main_zone_request('GET', rxv.rxv.BasicStatusGet)
        self.assertEqual(
            response.find("Main_Zone/Basic_Status/Speaker_Preout/Speaker_AB/Speaker_A").text,
            "On"
        )
        self.assertEqual(
            response.find("Main_Zone/Basic_Status/Speaker_Preout/Speaker_AB/Speaker_B").text,
            "On"
        )

    @requests_mock.mock()
    def test_power_on_timing_sequence(self, m):
        m.get(DESC_XML, text=sample_content('rx-v579-desc.xml'))
        m.post(CTRL_URL, [
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Power_Control><Power></Power></Power_Control></Main_Zone></YAMAHA_AV>'},
            {'text': self._basic_status_xml(power="Standby")},
            {'text': self._basic_status_xml(power="On")},
        ])

        rec = rxv.RXV(CTRL_URL)
        rec._request('PUT', rxv.rxv.PowerControl.format(state="On"))
        immediate = rec._main_zone_request('GET', rxv.rxv.BasicStatusGet)
        delayed = rec._main_zone_request('GET', rxv.rxv.BasicStatusGet)
        self.assertEqual(immediate.find("Main_Zone/Basic_Status/Power_Control/Power").text, "Standby")
        self.assertEqual(delayed.find("Main_Zone/Basic_Status/Power_Control/Power").text, "On")

    @requests_mock.mock()
    def test_relative_volume_commands_zone1(self, m):
        m.get(DESC_XML, text=sample_content('rx-v579-desc.xml'))
        m.post(CTRL_URL, [
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Volume><Lvl></Lvl></Volume></Main_Zone></YAMAHA_AV>'},
            {'text': self._main_volume_xml('-490')},
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Volume><Lvl></Lvl></Volume></Main_Zone></YAMAHA_AV>'},
            {'text': self._main_volume_xml('-500')},
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Volume><Lvl></Lvl></Volume></Main_Zone></YAMAHA_AV>'},
            {'text': self._main_volume_xml('-450')},
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Volume><Lvl></Lvl></Volume></Main_Zone></YAMAHA_AV>'},
            {'text': self._main_volume_xml('-500')},
        ])

        rec = rxv.RXV(CTRL_URL)
        rec._main_zone_request('PUT', '<Volume><Lvl><Val>Up 1 dB</Val><Exp></Exp><Unit></Unit></Lvl></Volume>')
        self.assertEqual(rec._main_zone_request('GET', '<Volume><Lvl>GetParam</Lvl></Volume>').find('Main_Zone/Volume/Lvl/Val').text, '-490')
        rec._main_zone_request('PUT', '<Volume><Lvl><Val>Down 1 dB</Val><Exp></Exp><Unit></Unit></Lvl></Volume>')
        self.assertEqual(rec._main_zone_request('GET', '<Volume><Lvl>GetParam</Lvl></Volume>').find('Main_Zone/Volume/Lvl/Val').text, '-500')
        rec._main_zone_request('PUT', '<Volume><Lvl><Val>Up 5 dB</Val><Exp></Exp><Unit></Unit></Lvl></Volume>')
        self.assertEqual(rec._main_zone_request('GET', '<Volume><Lvl>GetParam</Lvl></Volume>').find('Main_Zone/Volume/Lvl/Val').text, '-450')
        rec._main_zone_request('PUT', '<Volume><Lvl><Val>Down 5 dB</Val><Exp></Exp><Unit></Unit></Lvl></Volume>')
        self.assertEqual(rec._main_zone_request('GET', '<Volume><Lvl>GetParam</Lvl></Volume>').find('Main_Zone/Volume/Lvl/Val').text, '-500')

    @requests_mock.mock()
    def test_relative_volume_commands_zone2(self, m):
        m.get(DESC_XML, text=sample_content('rx-v579-desc.xml'))
        m.post(CTRL_URL, [
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Volume><Zone_B><Lvl></Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>'},
            {'text': self._zone_b_volume_xml('-690')},
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Volume><Zone_B><Lvl></Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>'},
            {'text': self._zone_b_volume_xml('-700')},
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Volume><Zone_B><Lvl></Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>'},
            {'text': self._zone_b_volume_xml('-650')},
            {'text': '<YAMAHA_AV rsp="PUT" RC="0"><Main_Zone><Volume><Zone_B><Lvl></Lvl></Zone_B></Volume></Main_Zone></YAMAHA_AV>'},
            {'text': self._zone_b_volume_xml('-700')},
        ])

        rec = rxv.RXV(CTRL_URL)
        rec.zone = "Zone_B"
        rec._main_zone_request('PUT', '<Volume><Zone_B><Lvl><Val>Up 1 dB</Val><Exp></Exp><Unit></Unit></Lvl></Zone_B></Volume>')
        self.assertEqual(rec._main_zone_request('GET', '<Volume><Zone_B><Lvl>GetParam</Lvl></Zone_B></Volume>').find('Main_Zone/Volume/Zone_B/Lvl/Val').text, '-690')
        rec._main_zone_request('PUT', '<Volume><Zone_B><Lvl><Val>Down 1 dB</Val><Exp></Exp><Unit></Unit></Lvl></Zone_B></Volume>')
        self.assertEqual(rec._main_zone_request('GET', '<Volume><Zone_B><Lvl>GetParam</Lvl></Zone_B></Volume>').find('Main_Zone/Volume/Zone_B/Lvl/Val').text, '-700')
        rec._main_zone_request('PUT', '<Volume><Zone_B><Lvl><Val>Up 5 dB</Val><Exp></Exp><Unit></Unit></Lvl></Zone_B></Volume>')
        self.assertEqual(rec._main_zone_request('GET', '<Volume><Zone_B><Lvl>GetParam</Lvl></Zone_B></Volume>').find('Main_Zone/Volume/Zone_B/Lvl/Val').text, '-650')
        rec._main_zone_request('PUT', '<Volume><Zone_B><Lvl><Val>Down 5 dB</Val><Exp></Exp><Unit></Unit></Lvl></Zone_B></Volume>')
        self.assertEqual(rec._main_zone_request('GET', '<Volume><Zone_B><Lvl>GetParam</Lvl></Zone_B></Volume>').find('Main_Zone/Volume/Zone_B/Lvl/Val').text, '-700')


class TestMenuCursor(unittest.TestCase):

    def _input_sel(self, input_sel):
        return ''.join(
            [
                '<YAMAHA_AV rsp="GET" RC="0"><Main_Zone><Input><Input_Sel>',
                input_sel,
                '</Input_Sel></Input></Main_Zone></YAMAHA_AV>',
            ]
        )

    @requests_mock.mock()
    def test_net_radio(self, m):
        m.get(DESC_XML, text=sample_content('rx-v675-desc.xml'))
        m.post(CTRL_URL, text=sample_content('rx-v675-inputs-resp.xml'))
        rec = rxv.RXV(CTRL_URL)

        rec.input = 'NET RADIO'
        m.post(CTRL_URL, text=self._input_sel('NET RADIO'))

        rec.menu_up()
        self.assertIn(f'>{rxv.rxv.CURSOR_UP}<', m.last_request.text)
        self.assertIn('<List_Control>', m.last_request.text)

        rec.menu_down()
        self.assertIn(f'>{rxv.rxv.CURSOR_DOWN}<', m.last_request.text)
        self.assertIn('<List_Control>', m.last_request.text)

        rec.menu_sel()
        self.assertIn(f'>{rxv.rxv.CURSOR_SEL}<', m.last_request.text)
        self.assertIn('<List_Control>', m.last_request.text)

        rec.menu_return()
        self.assertIn(f'>{rxv.rxv.CURSOR_RETURN}<', m.last_request.text)
        self.assertIn('<List_Control>', m.last_request.text)

        rec.menu_return_to_home()
        self.assertIn(f'>{rxv.rxv.CURSOR_RETURN_TO_HOME}<', m.last_request.text)
        self.assertIn('<List_Control>', m.last_request.text)

        with self.assertRaises(rxv.exceptions.MenuActionUnavailable):
            rec.menu_left()
        with self.assertRaises(rxv.exceptions.MenuActionUnavailable):
            rec.menu_right()
        with self.assertRaises(rxv.exceptions.MenuActionUnavailable):
            rec.menu_on_screen()
        with self.assertRaises(rxv.exceptions.MenuActionUnavailable):
            rec.menu_top_menu()
        with self.assertRaises(rxv.exceptions.MenuActionUnavailable):
            rec.menu_menu()
        with self.assertRaises(rxv.exceptions.MenuActionUnavailable):
            rec.menu_option()
        with self.assertRaises(rxv.exceptions.MenuActionUnavailable):
            rec.menu_display()

    @requests_mock.mock()
    def test_tuner(self, m):
        m.get(DESC_XML, text=sample_content('rx-v675-desc.xml'))
        m.post(CTRL_URL, text=sample_content('rx-v675-inputs-resp.xml'))
        rec = rxv.RXV(CTRL_URL)

        rec.input = 'TUNER'
        m.post(CTRL_URL, text=self._input_sel('TUNER'))
        with self.assertRaises(rxv.exceptions.MenuUnavailable):
            rec.menu_up()

    @requests_mock.mock()
    def test_hdmi(self, m):
        m.get(DESC_XML, text=sample_content('rx-v675-desc.xml'))
        m.post(CTRL_URL, text=sample_content('rx-v675-inputs-resp.xml'))
        rec = rxv.RXV(CTRL_URL)

        rec.input = 'HDMI1'
        m.post(CTRL_URL, text=self._input_sel('HDMI1'))

        rec.menu_up()
        self.assertIn(f'>{rxv.rxv.CURSOR_UP}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_down()
        self.assertIn(f'>{rxv.rxv.CURSOR_DOWN}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_left()
        self.assertIn(f'>{rxv.rxv.CURSOR_LEFT}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_right()
        self.assertIn(f'>{rxv.rxv.CURSOR_RIGHT}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_sel()
        self.assertIn(f'>{rxv.rxv.CURSOR_SEL}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_return()
        self.assertIn(f'>{rxv.rxv.CURSOR_RETURN}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_return_to_home()
        self.assertIn(f'>{rxv.rxv.CURSOR_RETURN_TO_HOME}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_on_screen()
        self.assertIn(f'>{rxv.rxv.CURSOR_ON_SCREEN}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_top_menu()
        self.assertIn(f'>{rxv.rxv.CURSOR_TOP_MENU}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_menu()
        self.assertIn(f'>{rxv.rxv.CURSOR_MENU}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_option()
        self.assertIn(f'>{rxv.rxv.CURSOR_OPTION}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)

        rec.menu_display()
        self.assertIn(f'>{rxv.rxv.CURSOR_DISPLAY}<', m.last_request.text)
        self.assertIn('<Cursor_Control>', m.last_request.text)
