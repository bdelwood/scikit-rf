import pytest

try:
    import pyvisa

    from skrf.vi.vna.cmt.cobalt import Cobalt, TraceParameter
except ImportError:
    pytest.skip("pyvisa not installed", allow_module_level=True)


@pytest.fixture
def resource(mocker):
    resource = mocker.MagicMock(spec=pyvisa.resources.MessageBasedResource)
    mocker.patch("pyvisa.ResourceManager").return_value.open_resource.return_value = resource
    responses = {
        "SERV:CHAN:COUN?": "16",
        "SERV:CHAN:ACT?": "1",
        "SERV:CHAN1:TRAC:ACT?": "1",
        "*OPC?": "1",
        "*IDN?": "Copper Mountain Technologies, C4220, 12345, 1.0",
    }
    resource.query.side_effect = responses.__getitem__
    return resource


@pytest.mark.parametrize("command", ["SERV:CHAN:COUN?", "*IDN?"])
def test_init_closes_resource_on_failure(resource, command):
    query = resource.query.side_effect

    def failed_query(cmd):
        if cmd == command:
            raise ConnectionError("connection lost")
        return query(cmd)

    resource.query.side_effect = failed_query
    with pytest.raises(ConnectionError, match="connection lost"):
        Cobalt("TEST")

    resource.close.assert_called_once_with()


@pytest.mark.parametrize("parameter", ["A", "B", "R1", "R2"])
def test_receiver_parameter(resource, parameter):
    analyzer = Cobalt("TEST")
    resource.write.reset_mock()
    query = resource.query.side_effect
    resource.query.side_effect = lambda cmd: f"{parameter}(2)" if cmd == "CALC1:PAR1:DEF?" else query(cmd)

    analyzer.ch1.param_def = parameter

    resource.write.assert_called_once_with(f"CALC1:PAR1:DEF {parameter}")
    assert analyzer.ch1.param_def == TraceParameter(parameter)


def test_trigger_single_enables_active_channel(resource, mocker):
    analyzer = Cobalt("TEST")
    resource.write.reset_mock()

    analyzer.trigger_single()

    assert resource.write.call_args_list == [
        mocker.call("TRIG:SOUR BUS"),
        mocker.call("INIT1:CONT 1"),
        mocker.call("TRIG:SING"),
    ]
