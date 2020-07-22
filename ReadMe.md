# mcd2c

Generate C serialization/deserialization code from the minecraft-data protodef protocol spec

Requires [python-minecraft-data](https://github.com/SpockBotMC/python-minecraft-data)

## Usage

`python mcd2c.py [version]`

Will generate two files: `[version]_proto.c` and `[version]_proto.h`

The header file is pretty self explanatory, each packet gets four or five functions:

`int walk_[packet_name](char *source, size_t max_len)`

Validates a packet's layout in a buffer, returns `-1` on invalid or improper layout and the total size of the packet on success. Walk should always be called on a buffer before calling a decode function, because decode doesn't do any bounds checking.

`size_t size_[packet_name]([packet_type] packet)`

Calculates the size of the packet when serialized, so you can know the amount of free space you need in the destination buffer. Size should always be called on a packet before calling an encode function, because encode doesn't do any bounds checking.

`char * enc_[packet_name](char *dest, [packet_type] packet)`

Serializes the packet into the destination buffer, returns a pointer to the end of the serialized packet.

`char * dec_[packet_name]([packet_type] *dest, char *source)`

Deserializes the buffer into the destination packet, returns a pointer to the end of the deserialized buffer.

`void free_[packet_name]([packet_type] packet)`

Frees dynamically allocated memory for packets that have dynamic-memory types, not present for packets that don't require dynamic memory allocation.
