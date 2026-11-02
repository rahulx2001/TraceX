import pytest

from scripts.audit_development_campaigns import census


def line(campaign='SYN1', year='2018', date='20180101', make='FORD'):
    fields = [b''] * 20
    for index, value in {1:campaign, 2:make, 3:'TEST', 4:year, 6:'FUEL SYSTEM, GASOLINE',
                         10:'V', 15:date}.items():
        fields[index] = value.encode()
    fields[19] = b'\xff\xfe synthetic outcome text must never be decoded'
    return b'\t'.join(fields) + b'\n'


def test_campaign_ids_not_vehicle_rows_are_counted():
    result = census([line(), line(year='2019'), line(), line(campaign='SYN2')])
    assert set(result) == {'SYN1', 'SYN2'}
    assert result['SYN1']['scope_rows'] == 2


def test_date_filter_precedes_scope_or_outcome_parsing():
    opened = line(date='20260101').replace(b'FORD', b'\xff\xfe')
    assert census([opened, line(date='20140101'), line(year='2014'), line(make='OTHER')]) == {}


def test_bad_date_cannot_silently_establish_a_complete_census():
    with pytest.raises(ValueError, match='completeness not established'):
        census([line(date='invalid')])
