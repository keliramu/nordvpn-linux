from lib import (
    daemon,
    dns,
    info,
    logging,
    login,
    settings
)
import lib
import pytest
import sh
import timeout_decorator


def setup_module(module):
    daemon.start()
    login.login_as("default")


def teardown_module(module):
    sh.nordvpn.logout("--persist-token")
    daemon.stop()


def setup_function(function):
    logging.log()

    # Make sure that Custom DNS, IPv6 and Threat Protection Lite are disabled before we execute each test 
    lib.set_dns("off")
    lib.set_ipv6("off")
    lib.set_threat_protection_lite("off")


def teardown_function(function):
    logging.log(data=info.collect())
    logging.log()


@pytest.mark.parametrize("threat_protection_lite", lib.THREAT_PROTECTION_LITE)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_tpl_connect(tech, proto, obfuscated, threat_protection_lite):
    lib.set_technology_and_protocol(tech, proto, obfuscated)
    lib.set_threat_protection_lite(threat_protection_lite)

    # Make sure, that DNS is unset before we connect to VPN server
    assert dns.is_unset()

    with lib.Defer(sh.nordvpn.disconnect):
        sh.nordvpn.connect()

        if threat_protection_lite == "on":
            assert settings.get_is_tpl_enabled()
            assert settings.dns_visible_in_settings("disabled")
            assert dns.is_set_for(dns.DNS_TPL)
        else:
            assert not settings.get_is_tpl_enabled()
            assert settings.dns_visible_in_settings("disabled")
            assert dns.is_set_for(dns.DNS_NORD)

    # Make sure, that DNS is unset, after we disconnect from VPN server
    assert dns.is_unset()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_set_tpl_connected(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    assert dns.is_unset()

    with lib.Defer(sh.nordvpn.disconnect):
        sh.nordvpn.connect()

        assert not settings.get_is_tpl_enabled()
        assert settings.dns_visible_in_settings("disabled")
        assert dns.is_set_for(dns.DNS_NORD)

        lib.set_threat_protection_lite("on")

        assert settings.get_is_tpl_enabled()
        assert settings.dns_visible_in_settings("disabled")
        assert dns.is_set_for(dns.DNS_TPL)

    assert dns.is_unset()


@pytest.mark.parametrize("nameserver", dns.DNS_CASES_CUSTOM)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_tpl_on_set_custom_dns_disconnected(tech, proto, obfuscated, nameserver):
    nameserver = nameserver.split(" ")

    lib.set_technology_and_protocol(tech, proto, obfuscated)

    sh.nordvpn.set.tpl("on")
    assert settings.get_is_tpl_enabled()

    output = sh.nordvpn.set.dns(nameserver)

    assert dns.TPL_MSG_WARNING_DISABLING in output
    assert not settings.get_is_tpl_enabled()
    assert settings.dns_visible_in_settings(nameserver)
    assert dns.is_unset()


@pytest.mark.parametrize("nameserver", dns.DNS_CASES_CUSTOM)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_tpl_on_set_custom_dns_connected(tech, proto, obfuscated, nameserver):
    nameserver = nameserver.split(" ")

    lib.set_technology_and_protocol(tech, proto, obfuscated)

    with lib.Defer(sh.nordvpn.disconnect):
        sh.nordvpn.connect()
        sh.nordvpn.set.tpl("on")
        assert settings.get_is_tpl_enabled()

        output = sh.nordvpn.set.dns(nameserver)
        assert dns.TPL_MSG_WARNING_DISABLING in output
        assert not settings.get_is_tpl_enabled()
        assert settings.dns_visible_in_settings(nameserver)
        assert dns.is_set_for(nameserver)

    assert dns.is_unset()



@pytest.mark.parametrize("nameserver", dns.DNS_CASES_CUSTOM)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_custom_dns_connect(tech, proto, obfuscated, nameserver):
    nameserver = nameserver.split(" ")

    lib.set_technology_and_protocol(tech, proto, obfuscated)
    sh.nordvpn.set.dns(nameserver)

    assert dns.is_unset()

    with lib.Defer(sh.nordvpn.disconnect):
        sh.nordvpn.connect()

        assert not settings.get_is_tpl_enabled()
        assert settings.dns_visible_in_settings(nameserver)
        assert dns.is_set_for(nameserver)

    assert dns.is_unset()


@pytest.mark.parametrize("nameserver", dns.DNS_CASES_CUSTOM)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_custom_dns_off_connect(tech, proto, obfuscated, nameserver):
    nameserver = nameserver.split(" ")

    lib.set_technology_and_protocol(tech, proto, obfuscated)

    sh.nordvpn.set.dns(nameserver)
    assert settings.dns_visible_in_settings(nameserver)
    assert dns.is_unset()

    sh.nordvpn.set.dns("off")
    assert settings.dns_visible_in_settings("disabled")
    assert dns.is_unset()

    with lib.Defer(sh.nordvpn.disconnect):
        sh.nordvpn.connect()
        assert dns.is_set_for(dns.DNS_NORD)

    assert dns.is_unset()


@pytest.mark.parametrize("nameserver", dns.DNS_CASES_CUSTOM)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_set_custom_dns_connected(tech, proto, obfuscated, nameserver):
    nameserver = nameserver.split(" ")

    lib.set_technology_and_protocol(tech, proto, obfuscated)

    with lib.Defer(sh.nordvpn.disconnect):
        sh.nordvpn.connect()
        sh.nordvpn.set.dns(nameserver)

        assert settings.dns_visible_in_settings(nameserver)
        assert dns.is_set_for(nameserver)

    assert dns.is_unset()


@pytest.mark.parametrize("nameserver", dns.DNS_CASES_CUSTOM)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_set_custom_dns_off_connected(tech, proto, obfuscated, nameserver):
    nameserver = nameserver.split(" ")

    lib.set_technology_and_protocol(tech, proto, obfuscated)

    with lib.Defer(sh.nordvpn.disconnect):
        sh.nordvpn.connect()

        sh.nordvpn.set.dns(nameserver)
        assert settings.dns_visible_in_settings(nameserver)
        assert dns.is_set_for(nameserver)

        sh.nordvpn.set.dns("off")
        assert settings.dns_visible_in_settings("disabled")
        assert dns.is_set_for(dns.DNS_NORD)

    assert dns.is_unset()


@pytest.mark.parametrize("nameserver,expected_error", dns.DNS_CASES_ERROR)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_custom_dns_errors_disconnected(tech, proto, obfuscated, nameserver, expected_error):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    with pytest.raises(sh.ErrorReturnCode_1) as ex:
        sh.nordvpn.set.dns(nameserver)

    assert expected_error in str(ex)
    assert settings.dns_visible_in_settings("disabled")
    assert dns.is_unset()


@pytest.mark.parametrize("nameserver,expected_error", dns.DNS_CASES_ERROR)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_custom_dns_errors_connected(tech, proto, obfuscated, nameserver, expected_error):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    with lib.Defer(sh.nordvpn.disconnect):
        sh.nordvpn.connect()

        with pytest.raises(sh.ErrorReturnCode_1) as ex:
            sh.nordvpn.set.dns(nameserver)

        assert expected_error in str(ex)
        assert settings.dns_visible_in_settings("disabled")
        assert dns.is_set_for(dns.DNS_NORD)

    assert dns.is_unset()


@pytest.mark.parametrize("nameserver", dns.DNS_CASES_CUSTOM)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_custom_dns_already_set_disconnected(tech, proto, obfuscated, nameserver):
    nameserver = nameserver.split(" ")
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    sh.nordvpn.set.dns(nameserver)
    assert dns.is_unset()

    with pytest.raises(sh.ErrorReturnCode_1) as ex:
        sh.nordvpn.set.dns(nameserver)

    full_error_message = dns.DNS_MSG_ERROR_ALREADY_SET % ", ".join(nameserver)

    assert full_error_message in str(ex)
    assert settings.dns_visible_in_settings(nameserver)
    assert dns.is_unset()


@pytest.mark.parametrize("nameserver", dns.DNS_CASES_CUSTOM)
@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_custom_dns_already_set_connected(tech, proto, obfuscated, nameserver):
    nameserver = nameserver.split(" ")

    lib.set_technology_and_protocol(tech, proto, obfuscated)

    sh.nordvpn.set.dns(nameserver)
    assert dns.is_unset()

    with lib.Defer(sh.nordvpn.disconnect):
        sh.nordvpn.connect()

        with pytest.raises(sh.ErrorReturnCode_1) as ex:
            sh.nordvpn.set.dns(nameserver)

        full_error_message = dns.DNS_MSG_ERROR_ALREADY_SET % ", ".join(nameserver)
        assert full_error_message in str(ex)
        assert settings.dns_visible_in_settings(nameserver)
        assert dns.is_set_for(nameserver)

    assert dns.is_unset()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_custom_dns_already_disabled_disconnected(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    with pytest.raises(sh.ErrorReturnCode_1) as ex:
        sh.nordvpn.set.dns("off")

    assert dns.DNS_MSG_ERROR_ALREADY_DISABLED in str(ex)
    assert settings.dns_visible_in_settings("disabled")
    assert dns.is_unset()


@pytest.mark.parametrize("tech,proto,obfuscated", lib.TECHNOLOGIES)
@pytest.mark.flaky(reruns=2, reruns_delay=90)
@timeout_decorator.timeout(40)
def test_custom_dns_already_disabled_connected(tech, proto, obfuscated):
    lib.set_technology_and_protocol(tech, proto, obfuscated)

    with lib.Defer(sh.nordvpn.disconnect):
        sh.nordvpn.connect()

        with pytest.raises(sh.ErrorReturnCode_1) as ex:
            sh.nordvpn.set.dns("off")

        assert settings.dns_visible_in_settings("disabled")
        assert dns.DNS_MSG_ERROR_ALREADY_DISABLED in str(ex)
        assert dns.is_set_for(dns.DNS_NORD)

    assert dns.is_unset()