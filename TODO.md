6- Discriminator fieldi hangi field secersek secelim ilk bytte arıyor, bu da benim kullanmam ve tanımlamam gereken mesajlarda hiçbir şekilde deserialization yapamamama neden oldu.(1.) (+)

13- Bitfield bulunan bir mesaj kullanıldığında fields.py:248'te "int object has no attribute 'get'" hatası alınıyor ve gercektende int'in get methodu yok. Bir sebeple value, bitfield'in default değeri olan 0'a eşit oluyor. Detaylı inceleme gerekmekte. BitField'in default=0 parametresi silinince sorunun ortadan kalktığı görülmüştür ancak bunun çözümü sağlanmalı (2.) (+)

11- Her field ve enumeration icin endianness bilgisinin girilebilmesi (4.) (+)

3- EnumField'ların kaç byte uzunlukta olacakları belirtilemiyor(6.) (+)

2- Field'ların hem is\_checksum hem de is\_timestamp olarak tiklenebilirliğini kaldırmak(7.) (+)





12- Checksum olan Fieldlar için seçilebilir algoritmalar eklenmeli ve ayarlanabilmeli bunu yanında checksumun hangi field'dan hangi fielda kadar ki aralıkta yapılacağı kullanıcı tarafından seçilebilmeli. Benim halihazırda bulunan checksum paketimle hesaplanmalı. CRC16 CRC32 AdditiveWord ByteSum ByteSumOnesComplement ByteSumTwosComplement Xor. (3.) (Checksum start end fieldlar string olarak yazılması gerekiyor gibi görünüyor UI'da bunun çözülmesi lazım. Çözülmüş gibi görünüyor +)

4- is\_timestamp true set edilen fieldlara serializer timestamp assign etmiyor on serialization belki ms mi s mi olarak unit de sorup ona göre bir atama yapılabilir(5.) (+)





10- String-based message desteğinin nasıl eklenebileceği düsünülecek. Belki telemetry studio açılırken ve sonradan değiştirilebilecek bir mod seçimi ekranı eklenebilir Hex<->String (8.) (+ and ready to be tested comprehensively)





5- Enum Manager'de enumerationlara SPL config ayarlanabilmesi(9.)

7- Mesajlar için seçilebilen configler tickbox ile seçilebilir olsun(13.)





1- Yeni Type'lar tanımlama, UI kullanımı, Middleware'de kullanımları vb. teknik ve teknik olmayan her türlü şey için dokümantasyon hazırlama (12.)





8- Halihazırda bulunan bir yapıda olan örnek bir xml ile load/save mappininin yapılması(10.)

9- Düz FieldType için bir repeat ve repeat ref eklenmesi düşünülebilir(11.)











<0000#RET,PING~CS>



3- Her türlü Field typeını kapsayan kapsamlı testler/benchmarklar yapmak (bu biraz denendi aslında)

