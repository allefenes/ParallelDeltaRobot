# Örnek liste
liste = [[1, 'a', 3], [2, 'b', 4], [3, 'c', 5]]

# 0'ıncı sütundaki değerleri saklayacak yeni bir liste oluşturun
sütun_değeri = []

# Listenin her bir alt listesi için 0'ıncı sütundaki değeri alın
for alt_liste in liste:
    sütun_değeri.append(alt_liste[0])

# Elde edilen 0'ıncı sütun değerlerini görüntüleyin
print(sütun_değeri)
