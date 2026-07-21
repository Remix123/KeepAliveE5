# Usage

Set the following repo secrets, then generate the first `refresh_token` locally. GitHub Actions should only run `Invoke API` after an encrypted `config/app0.json` exists.

| Name   | Value                                                             |
| ------ | ----------------------------------------------------------------- |
| PAT    | Github personal access token with `workflow` permission           |
| CONFIG_KEY | Encryption key for `config/*.json` token files                |

## Local device-code login

Create an Entra app registration, enable public client flows, add the delegated Microsoft Graph permissions you need, then run:

```bash
python3 scripts/get_refresh_token.py \
  --client-id "<Application client ID>" \
  --output config/app0.json
```

The script prints a verification URL and user code locally. Complete MFA in your browser; the script then saves the refresh token config for `Invoke API`.

Encrypt the generated config before committing it:

```bash
CONFIG_KEY="<same value as the GitHub secret>" python3 crypto.py e
git add config/app0.json
git commit -m "add encrypted graph config"
git push
```

<right><p align="right"><code>version@202410241807</code></p></right>
