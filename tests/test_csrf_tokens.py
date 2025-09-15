
def test_csrf_tokens_present(client):
    resp = client.get('/login')
    assert b"name='csrf_token'" in resp.data

    resp = client.get('/donate')
    assert b"name='csrf_token'" in resp.data

    resp = client.get('/prayers')
    assert b"name='csrf_token'" in resp.data
