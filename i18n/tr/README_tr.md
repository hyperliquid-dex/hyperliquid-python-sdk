# hyperliquid-python-sdk

<div align="center">

[![Dependencies Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/pulls?utf8=%E2%9C%93&q=is%3Apr%20author%3Aapp%2Fdependabot)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/.pre-commit-config.yaml)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/releases)
[![License](https://img.shields.io/pypi/l/hyperliquid-python-sdk)](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/LICENSE.md)

Python ile Hyperliquid API ticareti için SDK.
<h4 align="center">
    <p>
        <a href="README.md">English</a> |
        <b>Türkçe</b> |
    </p>
</h4>

</div>

## Kurulum
```bash
pip install hyperliquid-python-sdk
```
## Yapılandırma 

- `account_address` olarak genel anahtarı examples/config.json dosyasında ayarlayın.
- `secret_key` olarak özel anahtarınızı examples/config.json dosyasında ayarlayın.
- examples/example_utils.py dosyasında yapılandırmanın nasıl yüklendiğine dair örneğe bakın.

### [Opsiyonel] Bir API Cüzdanı için yeni bir API anahtarı oluşturun
https://app.hyperliquid.xyz/API adresinde yeni bir API özel anahtarı oluşturun ve yetkilendirin, ardından bu API cüzdanının özel anahtarını examples/config.json içinde `secret_key` olarak ayarlayın. Ana cüzdanın genel anahtarını hala `account_address` olarak ayarlamanız gerektiğini unutmayın.

## Kullanım Örnekleri
```python
from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.TESTNET_API_URL, skip_ws=True)
user_state = info.user_state("0xcd5051944f780a621ee62e39e493c489668acf4d")
print(user_state)
```
Daha kapsamlı örnekler için [examples](examples) klasörüne bakın. Ayrıca repoyu indirip özel anahtarınızı yapılandırdıktan sonra örnekleri çalıştırabilirsiniz örneğin:
```bash
cp examples/config.json.example examples/config.json
vim examples/config.json
python examples/basic_order.py
```

## Bu depoya katkıda bulunmaya başlama

1. `Poetry` indir: https://python-poetry.org/. 
   - Kurulum betiğinde `symlinks=True` ayarlamanız gerekebilir.
   - Poetry v2 desteklenmez bu yüzden belirli bir sürüm kurmanız gerekir örn: curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.4.1 python3 - 

2. Poetry'yi doğru Python sürümüne yönlendirin. Geliştirme için tam olarak python 3.10 gerekir. 3.11 sürümünde bazı bağımlılıklar sorun çıkarır, daha eski sürümler ise doğru tip desteğine sahip değildir.
`brew install python@3.10 && poetry env use /opt/homebrew/Cellar/python@3.10/3.10.16/bin/python3.10`

3. Bağımlılıkları kurun:

```bash
make install
```

### Makefile kullanımı

Daha hızlı geliştirme için CLI komutları. Daha fazla ayrıntı için `make help` komutuna bakın.

```bash
check-safety          Bağımlılıkları güvenlik açısından kontrol et
cleanup               Projeyi temizle
install               poetry.lock dosyasından bağımlılıkları yükle
install-types         mypy için ek tipleri bul ve yükle
lint                  pre-commit hedefi için kısayol
lockfile-update       poetry.lock dosyasını güncelle
lockfile-update-full  poetry.lock dosyasını tamamen yeniden oluştur
poetry-download       poetry indir ve yükle
pre-commit            Linters + formatlayıcıları pre-commit üzerinden çalıştır, yalnızca black çalıştırmak için "make pre-commit hook=black" kullan
test                  pytest ile testleri çalıştır
update-dev-deps       Geliştirme bağımlılıklarını en son sürümlere güncelle
```

## Sürümler

Mevcut sürümlerin listesine [GitHub Releases](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/releases) sayfasından bakabilirsiniz.

Biz [Semantic Versions](https://semver.org/) standardını takip ediyoruz ve [`Release Drafter`](https://github.com/marketplace/actions/release-drafter) kullanıyoruz. Pull requestler birleştirildikçe değişikliklerin listelendiği bir taslak sürüm güncel tutulur ve yayınlamaya hazır hale gelir. Kategoriler seçeneği ile sürüm notlarında pull requestleri etiketlere göre sınıflandırabilirsiniz.

### Etiketler ve karşılık gelen başlıklar

|               **Etiket**               |  **Sürümlerde Başlık**  |
| :-----------------------------------: | :---------------------: |
|       `enhancement`, `feature`        |        Özellikler       |
| `bug`, `refactoring`, `bugfix`, `fix` |  Düzeltmeler & Refaktör |
|       `build`, `ci`, `testing`        |  Build Sistemi & CI/CD  |
|              `breaking`               |  Kırıcı Değişiklikler   |
|            `documentation`            |     Dokümantasyon       |
|            `dependencies`             |  Bağımlılık Güncellemeleri |

### Yeni sürüm oluşturma ve yayınlama

Yeni bir sürüm oluşturma adımları:

- `poetry version <sürüm>` ile paketinizin sürümünü artırın. Yeni sürümü açıkça belirtebilir veya `major`, `minor` ya da `patch` gibi kurallar verebilirsiniz. Daha fazla ayrıntı için [Semantic Versions](https://semver.org/) standardına bakın.
- `GitHub`'a commit atın
- Bir `GitHub release` oluşturun
- `poetry publish --build`

## Lisans

Bu proje `MIT` lisansı altında lisanslanmıştır. Daha fazla ayrıntı için [LICENSE](LICENSE.md) dosyasına bakın.

```bibtex
@misc{hyperliquid-python-sdk,
  author = {Hyperliquid},
  title = {Python ile Hyperliquid API ticareti için SDK.},
  year = {2024},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/hyperliquid-dex/hyperliquid-python-sdk}}
}
```

## Katkılar

Bu proje [`python-package-template`](https://github.com/TezRomacH/python-package-template) ile oluşturulmuştur.
