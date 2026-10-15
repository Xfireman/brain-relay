import copy
import json
import pytest
from brain_relay.relay import validate_capsule, render_handoff, ValidationError, BudgetExceeded


def capsule():
    return dict(schema_version=1,id='sample-1',title='春日步道 🌿',goal='做一份双语地图\n可离线使用',context='两位志愿者\n第一轮已结束',
        decisions=[dict(text='使用纸质地图',source='讨论 A，第 3 条',confirmed=True,recorded_at='2026-01-01T10:00:00Z'),
                   dict(text='可能加二维码',source='讨论 A，第 4 条',confirmed=False,recorded_at='2026-01-01T10:00:00Z')],
        rejected=[dict(text='不要收集游客位置',source='讨论 A，第 5 条',confirmed=True,recorded_at='2026-01-01T10:00:00Z')],
        next_steps=[dict(text='核对公交站\n带上纸笔 📝',source='讨论 A，第 6 条',confirmed=False,recorded_at='2026-01-01T10:00:00Z')],
        sources=[dict(title='合成讨论',reference='讨论 A\n只用于演示',recorded_at='2026-01-01T10:00:00Z')],
        updated_at='2026-01-01T10:00:00Z',origin='manual')


def test_unicode_roundtrip_preserves_newlines_and_boolean_states():
    original=capsule()
    restored=validate_capsule(json.loads(json.dumps(original, ensure_ascii=False)))
    assert restored==original
    assert restored['decisions'][0]['confirmed'] is True
    assert restored['decisions'][1]['confirmed'] is False


def test_handoff_separates_candidates_and_rejected_from_actions():
    text=render_handoff(capsule())
    assert 'Confirmed decisions / 已确认决定\n' in text
    assert 'Candidate decisions / 待确认决定\n' in text
    confirmed=text.split('Confirmed decisions / 已确认决定\n')[1].split('Candidate decisions / 待确认决定\n')[0]
    candidate=text.split('Candidate decisions / 待确认决定\n')[1].split('Rejected approaches / 废弃方案')[0]
    actions=text.split('Next steps / 下一步\n')[1].split('Sources / 资料引用')[0]
    assert '使用纸质地图' in confirmed and '可能加二维码' not in confirmed
    assert '可能加二维码' in candidate
    assert '不要收集游客位置' not in actions
    assert '核对公交站\n带上纸笔 📝' in actions
    assert '讨论 A，第 3 条' in text and '2026-01-01T10:00:00Z' in text


def test_budget_does_not_emit_silently_partial_handoff():
    with pytest.raises(BudgetExceeded) as error:
        render_handoff(capsule(),20)
    assert error.value.required_chars > 20
    assert error.value.omitted['decisions']==2
    assert error.value.omitted['rejected']==1
    assert len(render_handoff(capsule(),10000)) > 20


@pytest.mark.parametrize('bad',[None,[],{}, {'schema_version':2}, {'schema_version':True}])
def test_invalid_schema_rejected(bad):
    with pytest.raises(ValidationError): validate_capsule(bad)


@pytest.mark.parametrize('value',['false',0,None,[]])
def test_confirmed_is_never_coerced(value):
    data=capsule();data['decisions'][1]['confirmed']=value
    with pytest.raises(ValidationError): validate_capsule(data)


def test_unknown_export_fields_are_rejected_not_silently_shared():
    data=capsule();data['raw_conversation']='private source'
    with pytest.raises(ValidationError): validate_capsule(data)


def test_invalid_timestamp_and_oversized_content_rejected():
    data=capsule();data['updated_at']='yesterday'
    with pytest.raises(ValidationError): validate_capsule(data)
    data=capsule();data['goal']='x'*20001
    with pytest.raises(ValidationError): validate_capsule(data)
