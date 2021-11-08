"""Tests for ssim.opendss"""
import os.path
from pathlib import Path
import pytest
import opendssdirect as dssdirect
from ssim import opendss, dssutil, grid


@pytest.fixture(scope='function')
def data_dir(request):
    return Path(
        os.path.abspath(os.path.dirname(request.module.__file__))) / "data"


@pytest.fixture(scope='function')
def test_circuit(data_dir):
    yield opendss.DSSModel(data_dir / "test_circuit.dss")
    dssutil.run_command("clear")


@pytest.fixture(scope='function')
def wind_data(data_dir):
    """Loadshape data used for the wind generator."""
    with open(data_dir / "ZavWind.csv") as f:
        return list(float(x) for x in f)


def test_set_loadshape_class(test_circuit):
    test_circuit.loadshapeclass = opendss.LoadShapeClass.DAILY
    assert test_circuit.loadshapeclass == opendss.LoadShapeClass.DAILY
    test_circuit.loadshapeclass = opendss.LoadShapeClass.YEARLY
    assert test_circuit.loadshapeclass == opendss.LoadShapeClass.YEARLY


def test_loadshape_changes(test_circuit, wind_data):
    normalized_wind = list(map(lambda x: x / max(wind_data), wind_data))
    test_circuit.solve(3600.0)
    dssdirect.Generators.Name('gen1')
    assert (8000 * normalized_wind[3600 % 2400]
            == pytest.approx(dssdirect.Generators.kW(), abs=5.0))
    active_power, reactive_power = test_circuit.total_power()
    test_circuit.solve(10*3600.0)  # hour 10
    assert (8000 * normalized_wind[(10 * 3600) % 2400]
            == pytest.approx(dssdirect.Generators.kW(), abs=5.0))
    active_power_ten, reactive_power_ten = test_circuit.total_power()
    assert active_power_ten != active_power
    assert reactive_power_ten != reactive_power


def test_DSSModel_node_voltage(test_circuit):
    test_circuit.solve(0)
    voltage = test_circuit.node_voltage('loadbus1')
    test_circuit.solve(10*3600)
    assert voltage != pytest.approx(test_circuit.node_voltage('loadbus1'))


def test_DSSModel_positive_sequence_voltage(test_circuit):
    test_circuit.solve(0)
    voltage = test_circuit.positive_sequence_voltage('loadbus1')
    test_circuit.solve(10*3600)
    assert voltage != pytest.approx(test_circuit.
                                    positive_sequence_voltage('loadbus1'))


def test_DSSModel_complex_voltage(test_circuit):
    test_circuit.solve(0)
    voltage = test_circuit.complex_voltage('loadbus1')
    test_circuit.solve(10 * 3600)
    assert voltage != pytest.approx(test_circuit.complex_voltage('loadbus1'))


def test_DSSModel_storage(test_circuit):
    test_circuit.add_storage(
        "TestStorage",
        "loadbus1",
        3,
        {"kwhrated": 5000, "kwrated": 1000, "kv": 12.47, "%stored": 50},
        state=opendss.StorageState.DISCHARGING
    )
    test_circuit.update_storage("TestStorage", 0.0, 0)
    test_circuit.solve(0)
    kw, kvar = test_circuit.total_power()
    test_circuit.update_storage("TestStorage", 1000, 0)
    test_circuit.solve(0)
    new_kw, _ = test_circuit.total_power()
    assert 900 < (new_kw - kw) < 1100
    test_circuit.update_storage("TestStorage", -1000, 0)
    test_circuit.solve(0)
    new_kw, _ = test_circuit.total_power()
    assert 900 < (kw - new_kw) < 1100


def test_DSSModel_add_pvsystem(test_circuit, data_dir):
    test_circuit.add_loadshape(
        "TestProfile", data_dir / "triangle.csv", 1.0, 24)
    test_circuit.add_pvsystem(
        "TestPV", "loadbus1", 3, 12.0, 12.0,
        {"kV": 12.47,
         "daily": "TestProfile",
         "temperature": 27,
         "irrad": 1000.0}
    )
    test_circuit.solve(0)
    dssdirect.PVsystems.Name("TestPV")
    assert dssdirect.PVsystems.kW() == pytest.approx(0.0)
    test_circuit.solve(3600 * 12)
    assert dssdirect.PVsystems.kW() == pytest.approx(12)


def test_DSSModel_add_xycurve(test_circuit):
    with pytest.raises(
            ValueError,
            match="`x_values` and `y_values` must be the same length"):
        test_circuit.add_xycurve("TestXY", [0, 0.5, 1.0], [1.0, 1.5])
    test_circuit.add_xycurve("TestXY", [0, 0.5, 1.0], [1.0, 1.5, 2.0])
    dssdirect.XYCurves.Name("TestXY")
    assert dssdirect.XYCurves.Npts() == 3
    assert dssdirect.XYCurves.XArray() == [0, 0.5, 1.0]
    assert dssdirect.XYCurves.YArray() == [1.0, 1.5, 2.0]


@pytest.fixture
def grid_spec(data_dir):
    """GridSpecification for the circuit defined in 'test_circuit.dss'."""
    dssdirect.run_command("clear")
    return grid.GridSpecification(data_dir / "test_circuit.dss")


def test_DSSModel_from_gridspec(grid_spec):
    model = opendss.DSSModel.from_grid_spec(grid_spec)
    assert len(model.storage_devices) == 0
    assert dssdirect.Circuit.Name() == "dssllibtestckt"


def test_DSSModel_from_gridspec_storage(grid_spec):
    grid_spec.add_storage(
        grid.StorageSpecification(
            name="S1",
            bus="loadbus1",
            kwh_rated=1000,
            kw_rated=100,
            phases=3,
            soc=0.11,
            controller='cycle'
        )
    )
    grid_spec.add_storage(
        grid.StorageSpecification(
            name="S2",
            bus="loadbus2.1.2",
            kwh_rated=2000,
            kw_rated=200,
            phases=2,
            soc=0.22,
            controller='cycle'
        )
    )
    model = opendss.DSSModel.from_grid_spec(grid_spec)
    assert len(model.storage_devices) == 2
    assert model.storage_devices["S1"].soc == pytest.approx(0.11)
    assert model.storage_devices["S1"].kwh_rated == 1000
    assert model.storage_devices["S1"].kw_rated == 100
    assert model.storage_devices["S2"].soc == pytest.approx(0.22)
    assert model.storage_devices["S2"].kwh_rated == 2000
    assert model.storage_devices["S2"].kw_rated == 200
    assert dssutil.get_property("storage.S2.phases") == '2'


def test_DSSModel_from_gridspec_pvsystem(grid_spec):
    pv_params = {
        "kV": 12.47,
        "irrad": 1000,
        "temperature": 25,
    }
    grid_spec.add_pvsystem(
        grid.PVSpecification(
            name="pv1",
            bus="loadbus1.1.2.3",
            pmpp=100.0,
            kva_rated=80.0,
            params=pv_params
        )
    )
    grid_spec.add_pvsystem(
        grid.PVSpecification(
            name="pv2",
            bus="loadbus2.2.3",
            pmpp=250.0,
            kva_rated=300.0,
            params=pv_params
        )
    )
    model = opendss.DSSModel.from_grid_spec(grid_spec)
    assert set(dssdirect.PVsystems.AllNames()) == {"pv1", "pv2"}
    dssdirect.PVsystems.Name("pv1")
    assert dssdirect.PVsystems.kVARated() == 80.0
    assert dssdirect.PVsystems.Pmpp() == 100.0
    dssdirect.Circuit.SetActiveBus("loadbus1")
    assert "PVSystem.pv1" in dssdirect.Bus.AllPCEatBus()
    dssdirect.Circuit.SetActiveBus("loadbus2")
    assert "PVSystem.pv2" in dssdirect.Bus.AllPCEatBus()


def test_DSSModel_from_gridspec_inverter_controller(grid_spec):
    pv_params = {
        "kV": 12.47,
        "irrad": 1000,
        "temperature": 25,
    }
    grid_spec.add_pvsystem(
        grid.PVSpecification(
            name="pv1",
            bus="loadbus1.1.2.3",
            pmpp=100.0,
            kva_rated=80.0,
            params=pv_params
        )
    )
    grid_spec.add_inv_control(
        grid.InvControlSpecification(
            name="invcontrol1",
            der_list=["PVSystem.pv1"],
            inv_control_mode="voltvar",
            function_curve=((0.5, 1.0), (0.95, 1.0), (1.0, 0.0),
                            (1.05, -1.0), (1.5, -1.0))
        )
    )
    model = opendss.DSSModel.from_grid_spec(grid_spec)
    list_of_ders = dssdirect.run_command("? invcontrol.invcontrol1.derlist")
    assert list_of_ders == '[PVSystem.pv1]'


def test_DSSModel_pvsystem_efficiency_curves(grid_spec):
    grid_spec.add_pvsystem(
        grid.PVSpecification(
            name="pv1",
            bus="loadbus2",
            pmpp=100,
            kva_rated=100,
            pt_curve=((0.0, 2.0), (2.0, 1.0), (3.0, 0.0)),
            inverter_efficiency=((0.1, 0.8), (0.5, 0.9),
                                 (0.8, 0.95), (1.0, 1.0))
        )
    )
    model = opendss.DSSModel.from_grid_spec(grid_spec)
    dssdirect.PVsystems.Name("pv1")
    eff_curve_name = dssdirect.run_command("? pvsystem.pv1.effcurve")
    dssdirect.XYCurves.Name(eff_curve_name)
    assert dssdirect.XYCurves.XArray() == [0.1, 0.5, 0.8, 1.0]
    assert dssdirect.XYCurves.YArray() == [0.8, 0.9, 0.95, 1.0]
    dssdirect.XYCurves.Name(dssdirect.run_command("? pvsystem.pv1.p-tcurve"))
    assert dssdirect.XYCurves.XArray() == [0.0, 2.0, 3.0]
    assert dssdirect.XYCurves.YArray() == [2.0, 1.0, 0.0]


def test_DSSModel_pvsystem_irradiance_profiles(grid_spec, data_dir):
    grid_spec.add_pvsystem(
        grid.PVSpecification(
            name="pv1",
            bus="loadbus2",
            pmpp=100,
            kva_rated=100,
            irradiance_profile=data_dir / "test_irradiance.csv"
        )
    )
    opendss.DSSModel.from_grid_spec(grid_spec)
    dssdirect.PVsystems.Name("pv1")
    irrad_profile_name = dssdirect.run_command("? pvsystem.pv1.daily")
    assert dssdirect.LoadShape.Name() == "irrad_pv_pv1"


def test_DSSModel_storage_efficiency_curves(grid_spec):
    storage_params = {
        "kV": 12.47
    }
    grid_spec.add_storage(
        grid.StorageSpecification(
            name="s1",
            bus="loadbus2",
            kwh_rated=1000,
            kw_rated=100,
            controller='cycle',
            params=storage_params,
            inverter_efficiency=((0.1, 0.8), (0.5, 0.9),
                                 (0.8, 0.95), (1.0, 1.0))
        )
    )
    model = opendss.DSSModel.from_grid_spec(grid_spec)
    eff_curve_name = dssdirect.run_command("? storage.s1.effcurve")
    dssdirect.XYCurves.Name(eff_curve_name)
    assert dssdirect.XYCurves.XArray() == [0.1, 0.5, 0.8, 1.0]
    assert dssdirect.XYCurves.YArray() == [0.8, 0.9, 0.95, 1.0]


def test_DSSModel_solution_time(test_circuit):
    assert test_circuit.next_update() == 0
    dssdirect.run_command("set controlmode=OFF")  # disable controls
    test_circuit.solve(0)
    delta = test_circuit.next_update()
    test_circuit.solve(delta)
    test_circuit.solve(delta + delta)
    next_time = test_circuit.next_update()
    assert next_time == delta * 3
    dssdirect.run_command("set controlmode=TIME")
    test_circuit.solve(next_time)
    # next update should be at a shorter interval with controls enabled.
    assert test_circuit.next_update() < delta * 4


def test_DSSModel_fail_line_restore_line(test_circuit):
    test_circuit.fail_line("line2", terminal=1, how='open')
    test_circuit.solve(7200)
    active_power, _ = test_circuit.total_power()
    test_circuit.restore_line("line2", terminal=1, how='closed')
    test_circuit.solve(7200)
    active_power_restored, _ = test_circuit.total_power()
    assert active_power < active_power_restored


@pytest.fixture
def test_circuit_fixed_gen(test_circuit):
    # make the wind generator a fixed generator so it no longer
    # follows a dispatch curve
    dssdirect.run_command("edit generator.gen1 status=fixed")
    return test_circuit


def test_Generator_change_setpoint(test_circuit_fixed_gen):
    gen = test_circuit_fixed_gen.generators["gen1"]
    gen.kw = 100.0
    assert gen.online
    test_circuit_fixed_gen.solve(1.0)
    old_power, _ = test_circuit_fixed_gen.total_power()
    gen.change_setpoint(0.0, 0.0)
    test_circuit_fixed_gen.solve(10.0)
    assert gen.online
    new_power, _ = test_circuit_fixed_gen.total_power()
    power_change = abs(new_power) - abs(old_power)
    assert power_change == pytest.approx(100.0, 1.0)
