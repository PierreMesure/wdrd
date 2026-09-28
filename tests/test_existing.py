import json
import subprocess
import sys
from unittest.mock import Mock
import pytest
from wdrd import export_docs, prepare_docs
from wdrd.existing import read_existing_documents

@pytest.mark.parametrize('header,separator', [('document_id', ','), ('P8433', '\t')])
def test_manual_list_replaces_sparql(tmp_path, monkeypatch, header, separator):
    path = tmp_path / 'existing.csv'
    path.write_text('\ufeff' + separator.join([header, 'item']) + '\n' + separator.join(['0001', 'http://www.wikidata.org/entity/Q123']) + '\n', encoding='utf-8')
    parsed = read_existing_documents(path)
    assert parsed.mapping == {'0001': 'Q123'}
    from wdrd.document import DocumentCollection
    forbidden = Mock(side_effect=AssertionError('SPARQL existence check'))
    monkeypatch.setattr(DocumentCollection, '_remove_existing_docs', forbidden)
    raw = [{'id': ident, 'rm': '2024/25', 'doktyp': 'mot', 'titel': 'Titel'} for ident in ['0001', '0002', '0002']]
    raw.append({'id': '0003', 'rm': '2024/25', 'doktyp': 'mot', 'titel': 'Motionen utgår'})
    collection = prepare_docs(raw, existing_documents=path)
    assert [d.doc_id for d in collection.docs] == ['0002']
    assert (collection.existing_count, collection.duplicate_count, collection.invalid_count) == (1, 1, 1)
    report = export_docs([], tmp_path / 'out.qs', filtered_documents=collection.filtered_documents)
    assert (report['existing'], report['duplicates'], report['invalid']) == (1, 1, 1)
    forbidden.assert_not_called()

def test_one_column_and_repeated_rows(tmp_path):
    path = tmp_path / 'ids.csv'
    path.write_text('document_id\n001\n001\nH9021\n')
    index = read_existing_documents(path)
    assert index.mapping == {'001': None, 'H9021': None}
    assert len(index.warnings) == 1
    assert index.warnings[0]['document_id'] == '001'

@pytest.mark.parametrize('content', [
    'document_id,qid\nH9021,Q1\nH9021,Q2\n',
    'document_id,qid\nH9021,not-a-qid\n',
    'document_id\nbad/id\n',
    'document_id\n""\n',
    'wrong_header\nH9021\n',
    'document_id,document_id\nH9021,H9021\n',
    'document_id,qid\nH9021\n',
])
def test_invalid_list_rejected_before_export(tmp_path, content):
    path = tmp_path / 'bad.csv'
    path.write_text(content)
    with pytest.raises(ValueError):
        read_existing_documents(path)

def test_missing_local_list_does_not_start_live_fetch():
    result = subprocess.run([sys.executable, '-m', 'wdrd', '--session', '2024/25', '--output', 'unused.qs'], capture_output=True, text=True)
    assert result.returncode == 2
    assert '--existing-documents FILE' in result.stderr

def test_malformed_list_does_not_start_live_fetch(tmp_path):
    path = tmp_path / 'bad.csv'
    path.write_text('document_id,qid\nH9021,Q1\nH9021,Q2\n')
    result = subprocess.run([sys.executable, '-m', 'wdrd', '--session', '2024/25', '--existing-documents', str(path), '--output', str(tmp_path / 'out.qs')], capture_output=True, text=True)
    assert result.returncode == 2
    assert 'Conflicting QIDs' in result.stderr
    assert not (tmp_path / 'out.qs').exists()
