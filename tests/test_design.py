"""Local usage constraints, not a promise that screenshots are aesthetically correct."""
from pathlib import Path
import re
import pytest

ROOT=Path(__file__).resolve().parents[1]/'brain_relay'


def tokens(theme):
    css=(ROOT/'static/tokens.css').read_text()
    light,dark=css.split('[data-theme="dark"]',1)
    values=dict(re.findall(r'--relay-([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;',light))
    if theme=='dark':values.update(re.findall(r'--relay-([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;',dark))
    return values


def luminance(color):
    channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in channels]
    return sum(x*y for x,y in zip(linear,(.2126,.7152,.0722)))


def contrast(first,second):
    a,b=sorted([luminance(first),luminance(second)])
    return (b+.05)/(a+.05)


@pytest.mark.parametrize('theme',['light','dark'])
def test_text_on_actual_surfaces_meets_contrast(theme):
    values=tokens(theme)
    # All information-bearing prose tokens occur on these solid page/card/input surfaces.
    for foreground in ('text','text-2','text-3','primary-text'):
        for background in ('bg','surface','surface-2','hover'):
            assert contrast(values[foreground],values[background])>=4.5,(theme,foreground,background)
    # Small primary button labels require text contrast, not the 3:1 graphical threshold.
    assert contrast(values['on-primary'],values['primary'])>=4.5


def violations(source):
    return re.findall(r'#[0-9a-fA-F]{3,8}\b|\brgba?\s*\(|\bhsla?\s*\(|100vh\b|transition\s*:\s*all|will-change\s*:|tabindex\s*=\s*["\'][1-9]|\.innerHTML\s*=|\.insertAdjacentHTML\s*\(',source)


def test_components_use_tokens_and_safe_interactions():
    for folder in ('static','templates'):
        for path in (ROOT/folder).glob('*'):
            if path.name=='tokens.css':continue
            text=path.read_text()
            assert not violations(text),(path.name,violations(text))
            assert not re.search(r'(?:src|href)=["\']https?://',text),path.name


def test_design_detector_catches_real_negative_examples():
    assert violations('.card{color:#fff;min-height:100vh;transition:all .2s} el.innerHTML = value')
    assert not violations('.card{color:var(--relay-text)} el.textContent = value')
