import numpy as np
import pytest
from voiceguard.metrics import metrics, calibrate, decision_metrics
from voiceguard.data import read_manifest


def test_perfect_and_inverted_metrics():
    perfect=metrics([0,0,1,1],[.1,.2,.8,.9])
    assert perfect['accuracy']==1 and perfect['eer_interpolated']==0
    assert perfect['confusion_matrix_real_fake']==[[2,0],[0,2]]
    inverted=metrics([0,0,1,1],[.9,.8,.2,.1])
    assert inverted['roc_auc']==0 and inverted['eer_interpolated']==1


def test_calibration_validates_counts_and_abstention():
    with pytest.raises(ValueError,match='at least'):
        calibrate([0,1],[.1,.9])
    y=[0]*20+[1]*20;scores=[.1]*20+[.9]*20
    calibration=calibrate(y,scores,max_error=0)
    assert calibration['real_threshold']<calibration['fake_threshold']
    stats=decision_metrics(y,scores,calibration)
    assert stats['coverage']==1 and stats['decided_accuracy']==1


def test_single_class_rejected():
    with pytest.raises(ValueError,match='both'):metrics([0,0],[.1,.2])


def test_manifest_rejects_speaker_leakage(tmp_path):
    (tmp_path/'a.wav').write_bytes(b'one')
    (tmp_path/'b.wav').write_bytes(b'two')
    csv=tmp_path/'manifest.csv'
    csv.write_text('path,label,speaker,language,split,consent\na.wav,real,same,ar,train,true\nb.wav,fake,same,ar,test,true\n')
    with pytest.raises(ValueError,match='Speaker leakage'):read_manifest(csv)


def test_manifest_rejects_missing_consent(tmp_path):
    csv=tmp_path/'manifest.csv';csv.write_text('path,label,speaker,language,split,consent\na.wav,real,s,ar,test,false\n')
    with pytest.raises(ValueError,match='consent'):read_manifest(csv)


def test_speech_gate_abstentions_are_not_counted_as_correct_classifications():
    result = decision_metrics([0, 0, 1, 1], [.1, .9, .9, .1],
                              {'real_threshold': .2, 'fake_threshold': .8},
                              eligible=[True, False, True, False])
    assert result['coverage'] == .5 and result['decided_count'] == 2
    assert result['decided_accuracy'] == 1
    assert result['speech_gate_abstentions'] == 2
    assert result['confusion_real_fake_inconclusive'] == [[1, 0, 1], [0, 1, 1]]


def test_all_abstained_has_no_decided_accuracy():
    result = decision_metrics([0, 1], [.1, .9], {'real_threshold': .2, 'fake_threshold': .8},
                              eligible=[False, False])
    assert result['coverage'] == 0 and result['decided_accuracy'] is None
