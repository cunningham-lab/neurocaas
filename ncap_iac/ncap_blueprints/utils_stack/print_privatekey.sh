raw_string=$(aws ssm get-parameter --name /testkeystack/neurocaas/private-dev-key --with-decryption )
value=$(jq .Parameter.Value <<< $raw_string | sed s/\"//g)
printf "%b" "$value"
