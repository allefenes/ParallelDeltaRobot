#!/usr/bin/env bash
# Yerel geliştirme için kendinden imzalı CA ve sunucu sertifikası üretir (yalnız yerel; gerçek
# sertifika ve alan adı kullanıcı kararıyla F4 sonrası). Çıktı dizini adlandırılmış Docker birimidir,
# çalışma ağacına dosya yazılmaz. Sertifikalar zaten varsa yeniden üretilmez.
#   kullanım: make_certs.sh <çıktı_dizini> [sunucu_adı ...]
set -euo pipefail

out="${1:?çıktı dizini}"
shift
names=("${@:-server}")
mkdir -p "$out"
cd "$out"

if [[ -f ca.crt && -f server.crt && -f server.key ]]; then
  echo "sertifikalar mevcut: $out"
  exit 0
fi

# CA (10 yıl, yalnız yerel)
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
  -keyout ca.key -out ca.crt -subj "/CN=DeltaRobotV2 yerel CA" >/dev/null 2>&1

# Sunucu anahtarı + SAN listesi (compose servis adı, localhost)
san="DNS:localhost,IP:127.0.0.1"
for n in "${names[@]}"; do san="$san,DNS:$n"; done
openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr \
  -subj "/CN=${names[0]}" >/dev/null 2>&1
printf "subjectAltName=%s\nextendedKeyUsage=serverAuth\n" "$san" >ext.cnf
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 825 -out server.crt -extfile ext.cnf >/dev/null 2>&1
rm -f server.csr ext.cnf ca.srl
chmod 644 ca.crt server.crt
chmod 600 ca.key
chmod 644 server.key # sunucu konteyneri farklı kullanıcıyla okuyabilsin (yalnız yerel geliştirme)
echo "sertifikalar üretildi: $out ($san)"
