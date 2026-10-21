"""Real temporary Git histories expose provenance tampering without network."""
from copy import deepcopy
from hashlib import sha256
import json
import subprocess

import pytest

from masck_one.adversarial_fit_proof import source_snapshot, FitProofError


@pytest.fixture
def history(tmp_path):
    def git(*args):
        return subprocess.check_output(['git',*args],cwd=tmp_path,stderr=subprocess.PIPE,text=True).strip()
    git('init','-q')
    git('config','user.name','Synthetic Fixture')
    git('config','user.email','fixture@example.invalid')
    folder=tmp_path/'analysis/fit_proof';folder.mkdir(parents=True)
    source=tmp_path/'src/part.py';source.parent.mkdir();source.write_text('original\n')
    doc=tmp_path/'docs/context.md';doc.parent.mkdir();doc.write_text('original context\n')
    git('add','src','docs');git('commit','-qm','Original fixture source')
    original=git('rev-parse','HEAD')
    source.write_text('current\n');doc.write_text('current context\n')
    git('add','src','docs');git('commit','-qm','Changed fixture source')
    current=git('rev-parse','HEAD')
    def row(path,commit):
        content=subprocess.check_output(['git','show',commit+':'+path],cwd=tmp_path)
        return {'path':path,'git_blob':git('rev-parse',commit+':'+path),
                'sha256':sha256(content).hexdigest()}
    data={'main':current,'original_analyzed_main':original,
          'consumed_files':[row('src/part.py',current),row('docs/context.md',current)]}
    def write(d):
        (folder/'sources.json').write_text(json.dumps(d))
    write(data)
    return tmp_path,data,write,row,git


def test_exact_commit_blob_and_worktree_chain_passes(history):
    root,data,*_=history
    assert source_snapshot(root)==data


@pytest.mark.parametrize('field',['git_blob','main','sha256'])
def test_single_provenance_field_tamper_fails(history,field):
    root,data,write,row,git=history
    if field=='main':data['main']=data['original_analyzed_main']
    else:data['consumed_files'][0][field]='a'*(40 if field=='git_blob' else 64)
    write(data)
    with pytest.raises(FitProofError,match='source'):source_snapshot(root)


def test_other_commit_bytes_and_local_hash_do_not_prove_release_membership(history):
    root,data,write,row,git=history
    (root/'src/part.py').write_text('original\n')
    data['consumed_files'][0]=row('src/part.py',data['original_analyzed_main'])
    write(data)
    with pytest.raises(FitProofError,match='source'):source_snapshot(root)


def test_explicit_per_row_source_commit_is_verified(history):
    root,data,write,row,git=history
    (root/'src/part.py').write_text('original\n')
    data['consumed_files'][0]={**row('src/part.py',data['original_analyzed_main']),
                               'source_commit':data['original_analyzed_main']}
    write(data)
    assert source_snapshot(root)==data
    data['consumed_files'][0]['source_commit']=data['main'];write(data)
    with pytest.raises(FitProofError):source_snapshot(root)


@pytest.mark.parametrize('bad',['main','HEAD','a'*40,None])
def test_missing_or_moving_commit_not_accepted(history,bad):
    root,data,write,*_=history
    data['main']=bad;write(data)
    with pytest.raises(FitProofError):source_snapshot(root)


def test_blob_cannot_impersonate_commit(history):
    root,data,write,*_=history
    data['main']=data['consumed_files'][0]['git_blob'];write(data)
    with pytest.raises(FitProofError):source_snapshot(root)


def test_local_changes_are_rechecked_after_cached_git_verification(history):
    root,data,*_=history
    source_snapshot(root)
    (root/'src/part.py').write_text('tampered after verification\n')
    with pytest.raises(FitProofError,match='stale'):source_snapshot(root)


def test_documentary_predecessor_requires_verified_original_commit(history):
    root,data,write,row,git=history
    old=row('docs/context.md',data['original_analyzed_main'])
    data['consumed_files'][1]['accepted_original_context_sha256']=old['sha256']
    (root/'docs/context.md').write_text('original context\n');write(data)
    assert source_snapshot(root)==data
    data['original_analyzed_main']=data['main'];write(data)
    with pytest.raises(FitProofError,match='predecessor'):source_snapshot(root)


def test_geometry_cannot_use_context_exception(history):
    root,data,write,*_=history
    data['consumed_files'][0]['accepted_original_context_sha256']=data['consumed_files'][0]['sha256']
    write(data)
    with pytest.raises(FitProofError,match='documentary'):source_snapshot(root)


@pytest.mark.parametrize('path',['../outside','/etc/passwd','src/../src/part.py','src//part.py','src/missing.py'])
def test_missing_or_escaping_paths_fail(history,path):
    root,data,write,*_=history
    data['consumed_files'][0]['path']=path;write(data)
    with pytest.raises(FitProofError):source_snapshot(root)


def test_duplicate_or_empty_source_set_cannot_pass(history):
    root,data,write,*_=history
    for rows in [[],data['consumed_files']+[deepcopy(data['consumed_files'][0])]]:
        data['consumed_files']=rows;write(data)
        with pytest.raises(FitProofError):source_snapshot(root)
