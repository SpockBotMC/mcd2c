#define _DEFAULT_SOURCE
#include <endian.h>
#undef _DEFAULT_SOURCE
#include "cNBT/nbt.h"
#include "datautils.h"
#include "sds.h"
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

// 2^30, when we need a max_len but we're sure we wont overflow
// What we really need is an "unsafe" version of functions we're passing this
// to
#define NO_OVERFLOW 1073741824

// Warning: Some deeply monotonous code is in this file.

// ProtoDef Numeric Types
char *enc_byte(char *dest, uint8_t source) {
	*dest = source;
	return dest + sizeof(source);
}

char *dec_byte(uint8_t *dest, char *source) {
	*dest = *source;
	return source + sizeof(*dest);
}

char *enc_be16(char *dest, uint16_t source) {
	memcpy(dest, &(uint16_t){htobe16(source)}, sizeof(source));
	return dest + sizeof(source);
}

char *dec_be16(uint16_t *dest, char *source) {
	*dest = be16toh(*(uint16_t *){memcpy(dest, source, sizeof(*dest))});
	return source + sizeof(*dest);
}

char *enc_be32(char *dest, uint32_t source) {
	memcpy(dest, &(uint32_t){htobe32(source)}, sizeof(source));
	return dest + sizeof(source);
}

char *dec_be32(uint32_t *dest, char *source) {
	*dest = be32toh(*(uint32_t *){memcpy(dest, source, sizeof(*dest))});
	return source + sizeof(*dest);
}

char *enc_be64(char *dest, uint64_t source) {
	memcpy(dest, &(uint64_t){htobe64(source)}, sizeof(source));
	return dest + sizeof(source);
}

char *dec_be64(uint64_t *dest, char *source) {
	*dest = be64toh(*(uint64_t *){memcpy(dest, source, sizeof(*dest))});
	return source + sizeof(*dest);
}

char *enc_le16(char *dest, uint16_t source) {
	memcpy(dest, &(uint16_t){htole16(source)}, sizeof(source));
	return dest + sizeof(source);
}

char *dec_le16(uint16_t *dest, char *source) {
	*dest = le16toh(*(uint16_t *){memcpy(dest, source, sizeof(*dest))});
	return source + sizeof(*dest);
}

char *enc_le32(char *dest, uint32_t source) {
	memcpy(dest, &(uint32_t){htole32(source)}, sizeof(source));
	return dest + sizeof(source);
}

char *dec_le32(uint32_t *dest, char *source) {
	*dest = le32toh(*(uint32_t *){memcpy(dest, source, sizeof(*dest))});
	return source + sizeof(*dest);
}

char *enc_le64(char *dest, uint64_t source) {
	memcpy(dest, &(uint64_t){htole64(source)}, sizeof(source));
	return dest + sizeof(source);
}

char *dec_le64(uint64_t *dest, char *source) {
	*dest = le64toh(*(uint64_t *){memcpy(dest, source, sizeof(*dest))});
	return source + sizeof(*dest);
}

char *enc_bef32(char *dest, float source) {
	uint32_t i = htobe32(*(uint32_t *) memcpy(&i, &source, sizeof(source)));
	memcpy(dest, &i, sizeof(source));
	return dest + sizeof(source);
}

char *dec_bef32(float *dest, char *source) {
	uint32_t i = be32toh(*(uint32_t *) memcpy(&i, source, sizeof(*dest)));
	memcpy(dest, &i, sizeof(*dest));
	return source + sizeof(*dest);
}

char *enc_bef64(char *dest, double source) {
	uint64_t i = htobe64(*(uint64_t *) memcpy(&i, &source, sizeof(source)));
	memcpy(dest, &i, sizeof(source));
	return dest + sizeof(source);
}

char *dec_bef64(double *dest, char *source) {
	uint64_t i = be64toh(*(uint64_t *) memcpy(&i, source, sizeof(*dest)));
	memcpy(dest, &i, sizeof(*dest));
	return source + sizeof(*dest);
}

char *enc_lef32(char *dest, float source) {
	uint32_t i = htole32(*(uint32_t *) memcpy(&i, &source, sizeof(source)));
	memcpy(dest, &i, sizeof(source));
	return dest + sizeof(source);
}

char *dec_lef32(float *dest, char *source) {
	uint32_t i = le32toh(*(uint32_t *) memcpy(&i, source, sizeof(*dest)));
	memcpy(dest, &i, sizeof(*dest));
	return source + sizeof(*dest);
}

char *enc_lef64(char *dest, double source) {
	uint64_t i = htole64(*(uint64_t *) memcpy(&i, &source, sizeof(source)));
	memcpy(dest, &i, sizeof(source));
	return dest + sizeof(source);
}

char *dec_lef64(double *dest, char *source) {
	uint64_t i = le64toh(*(uint64_t *) memcpy(&i, source, sizeof(*dest)));
	memcpy(dest, &i, sizeof(*dest));
	return source + sizeof(*dest);
}

char *enc_buffer(char *dest, mc_buffer source) {
	memcpy(dest, source.base, source.len);
	return dest + source.len;
}

char *dec_buffer(mc_buffer *dest, char *source, size_t len) {
	if(!(dest->base = malloc(len)))
		return NULL;
	dest->len = len;
	memcpy(dest->base, source, len);
	return source + len;
}

void free_buffer(mc_buffer buffer) { free(buffer.base); }

// size_ functions let you know how big a type structure is going to be whe
// its encoded into a memory buffer
// walk_ functions let you know how big a currently encoded type is, and
// will error if the type is invalid, they can't complete the walk, or max_len
// doesn't have enough room for the calculated size
size_t size_varint(uint32_t varint) {
	if(varint < (1 << 8))
		return 1;
	if(varint < (1 << 14))
		return 2;
	if(varint < (1 << 21))
		return 3;
	if(varint < (1 << 28))
		return 4;
	return 5;
}

int walk_varint(char *source, size_t max_len) {
	if(!max_len)
		return varnum_overrun;
	int len = 1;
	for(; *(unsigned char *)source & 0x80; source++, len++) {
		if(len > 4)
			return varnum_invalid;
		if((size_t)len > max_len)
			return varnum_overrun;
	}
	if((size_t)len > max_len)
		return varnum_overrun;
	return len;
}

char *enc_varint(char *dest, uint32_t source) {
	for(; source >= 0x80; dest++, source >>= 7) {
		*dest = 0x80 | (source & 0x7F);
	}
	*dest = source & 0x7F;
	return ++dest;
}

char *dec_varint(int32_t *dest, char *source) {
	for(; *(unsigned char *)source & 0x80; source++, *(uint32_t *)dest <<= 7) {
		*(uint32_t *)dest |= *source & 0x7F;
	}
	*(uint32_t *)dest |= *source & 0x7F;
	return ++source;
}

// Everything past this point isn't part of ProtoDef, just minecraft

size_t size_varlong(uint64_t varint) {
	if(varint < (1 << 8))
		return 1;
	if(varint < (1 << 14))
		return 2;
	if(varint < (1 << 21))
		return 3;
	if(varint < (1 << 28))
		return 4;
	if(varint < (1ULL << 35))
		return 5;
	if(varint < (1ULL << 42))
		return 6;
	if(varint < (1ULL << 49))
		return 7;
	if(varint < (1ULL << 56))
		return 8;
	if(varint < (1ULL << 63))
		return 9;
	return 10;
}

int walk_varlong(char *source, size_t max_len) {
	if(!max_len)
		return varnum_overrun;
	int len = 1;
	for(; *(unsigned char *)source & 0x80; source++, len++) {
		if(len > 9)
			return varnum_invalid;
		if((size_t)len > max_len)
			return varnum_overrun;
	}
	if((size_t)len > max_len)
		return varnum_overrun;
	return len;
}

char *enc_varlong(char *dest, uint64_t source) {
	for(; source >= 0x80; dest++, source >>= 7) {
		*dest = 0x80 | (source & 0x7F);
	}
	*dest = source & 0x7F;
	return ++dest;
}

char *dec_varlong(int64_t *dest, char *source) {
	for(; *(unsigned char *)source & 0x80; source++, *(uint64_t *)dest <<= 7) {
		*(uint64_t *)dest |= *source & 0x7F;
	}
	*(uint64_t *)dest |= *source & 0x7F;
	return ++source;
}

// Varint prefixed string
size_t size_string(sds string) {
	return size_varint(sdslen(string)) + sdslen(string);
}

int walk_string(char *source, size_t max_len) {
	int ret = walk_varint(source, max_len);
	if(ret < 0)
		return ret;
	int32_t len;
	dec_varint(&len, source);
	if(max_len < (size_t)ret + len)
		return -1;
	return ret + len;
}

char *enc_string(char *dest, sds source) {
	int32_t len = (int32_t)sdslen(source);
	return (char *)memcpy(enc_varint(dest, len), source, len) + len;
}

char *dec_string(sds *dest, char *source) {
	int32_t len;
	source = dec_varint(&len, source);
	*dest = sdsnewlen(source, (size_t)len);
	return source + len;
}

// Big Endian 128-bit uint
char *enc_uuid(char *dest, mc_uuid source) {
	return enc_be64(enc_be64(dest, source.msb), source.lsb);
}

char *dec_uuid(mc_uuid *dest, char *source) {
	return dec_be64(&dest->lsb, dec_be64(&dest->msb, source));
}

// From MSB to LSB x: 26-bits, y: 12-bits, z: 26-bits
// each is an independent signed 2-complement integer
char *enc_position(char *dest, mc_position source) {
	return enc_be64(dest, ((uint64_t)source.x & 0x3FFFFFF) << 38 |
														((uint64_t)source.y & 0xFFF) << 26 |
														(source.z & 0x3FFFFFF));
}

char *dec_position(mc_position *dest, char *source) {
	uint64_t i;
	source = dec_be64(&i, source);
	if((dest->x = i >> 38) >= 1 << 25)
		dest->x -= 1 << 26;
	if((dest->y = (i >> 26) & 0xFFF) >= 1 << 11)
		dest->y -= 1 << 12;
	if((dest->z = i & 0x3FFFFFF) >= 1 << 25)
		dest->z -= 1 << 26;
	return source;
}

size_t size_nbt_list(nbt_node *node) {
	size_t size = 0;
	struct list_head *pos;
	list_for_each(pos, &node->payload.tag_list->entry) {
		size += size_unnamed_nbt(list_entry(pos, struct nbt_list, entry)->data);
	}
	return size;
}

size_t size_nbt_compound(nbt_node *node) {
	size_t size = 1;
	struct list_head *pos;
	list_for_each(pos, &node->payload.tag_compound->entry) {
		nbt_node *member = list_entry(pos, struct nbt_list, entry)->data;
		if(!member->name) {
			size += sizeof(uint8_t) + sizeof(int16_t) + size_unnamed_nbt(member);
		} else {
			size += sizeof(uint8_t) + sizeof(int16_t) + strlen(member->name);
			size += size_unnamed_nbt(member);
		}
	}
	return size;
}

size_t size_unnamed_nbt(nbt_node *node) {
	switch(node->type) {
		case TAG_BYTE:
			return sizeof(char);
		case TAG_SHORT:
			return sizeof(int16_t);
		case TAG_INT:
			return sizeof(int32_t);
		case TAG_LONG:
			return sizeof(int64_t);
		case TAG_FLOAT:
			return sizeof(float);
		case TAG_DOUBLE:
			return sizeof(double);
		case TAG_BYTE_ARRAY:
			return sizeof(int32_t) + node->payload.tag_int_array.length;
		case TAG_INT_ARRAY:
			return sizeof(int32_t) +
						 node->payload.tag_int_array.length * sizeof(int32_t);
		case TAG_LONG_ARRAY:
			return sizeof(int32_t) +
						 node->payload.tag_int_array.length * sizeof(int64_t);
		case TAG_STRING:
			return sizeof(int16_t) + strlen(node->payload.tag_string);
		case TAG_LIST:
			return size_nbt_list(node);
		case TAG_COMPOUND:
			return size_nbt_compound(node);
		default:
			return 0;
	}
}

size_t size_nbt(nbt_node *nbt) {
	if(!nbt->name) {
		return sizeof(uint8_t) + sizeof(int16_t) + size_unnamed_nbt(nbt);
	} else {
		return sizeof(uint8_t) + sizeof(int16_t) + strlen(nbt->name) +
					 size_unnamed_nbt(nbt);
	}
}

int walk_nbt_string(char *source, size_t max_len) {
	uint16_t len;
	if(max_len < sizeof(len))
		return -1;
	dec_be16(&len, source);
	if(max_len < sizeof(len) + len)
		return -1;
	return sizeof(len) + len;
}

int walk_nbt_array(char *source, size_t max_len, size_t type_len) {
	uint32_t len;
	if(max_len < sizeof(len))
		return -1;
	dec_be32(&len, source);
	if(max_len < sizeof(len) + (len * type_len))
		return -1;
	return sizeof(len) + (len * type_len);
}

int walk_nbt_list(char *source, size_t max_len) {
	uint8_t type;
	int32_t count;
	int size = sizeof(type) + sizeof(count);
	if(max_len < (size_t)size)
		return -1;
	source = dec_byte(&type, source);
	source = dec_be32((uint32_t *)&count, source);
	for(int i = 0, step; i < count;
			 i++, source += step, max_len -= step, size += step) {
		step = walk_unnamed_nbt(source, type, max_len);
		if(step < 0)
			return -1;
	}
	return size;
}

int walk_nbt_compound(char *source, size_t max_len) {
	for(int tag_size, total_size = 0;;
			 source += tag_size, total_size += tag_size, max_len -= tag_size) {
		if(!max_len)
			return -1;
		uint8_t type;
		source = dec_byte(&type, source);
		total_size += sizeof(type);
		if(!type)
			return total_size;
		if((tag_size = walk_nbt_string(source, --max_len)) < 0)
			return -1;
		source += tag_size;
		total_size += tag_size;
		max_len -= tag_size;
		if((tag_size = walk_unnamed_nbt(source, type, max_len)) < 0)
			return -1;
	}
}

int walk_unnamed_nbt(char *source, nbt_type type, size_t max_len) {
	int size;
	switch(type) {
	case TAG_BYTE:
		size = sizeof(char);
		break;
	case TAG_SHORT:
		size = sizeof(int16_t);
		break;
	case TAG_INT:
		size = sizeof(int32_t);
		break;
	case TAG_LONG:
		size = sizeof(int64_t);
		break;
	case TAG_FLOAT:
		size = sizeof(float);
		break;
	case TAG_DOUBLE:
		size = sizeof(double);
		break;
	case TAG_BYTE_ARRAY:
		if((size = walk_nbt_array(source, max_len, sizeof(char))) < 0)
			return -1;
		break;
	case TAG_INT_ARRAY:
		if((size = walk_nbt_array(source, max_len, sizeof(int32_t))) < 0)
			return -1;
		break;
	case TAG_LONG_ARRAY:
		if((size = walk_nbt_array(source, max_len, sizeof(int64_t))) < 0)
			return -1;
		break;
	case TAG_STRING:
		if((size = walk_nbt_string(source, max_len)) < 0)
			return -1;
		break;
	case TAG_LIST:
		if((size = walk_nbt_list(source, max_len)) < 0)
			return -1;
		break;
	case TAG_COMPOUND:
		if((size = walk_nbt_compound(source, max_len)) < 0)
			return -1;
		break;
	default:
		return -1;
	}
	if(max_len < (size_t)size)
		return -1;
	return size;
}

int walk_nbt(char *source, size_t max_len) {
	if(!max_len)
		return -1;
	uint8_t type;
	int size, total = sizeof(type);
	source = dec_byte(&type, source);
	if((size = walk_nbt_string(source, --max_len)) < 0)
		return -1;
	source += size;
	total += size;
	max_len -= size;
	if((size = walk_unnamed_nbt(source, type, max_len)) < 0)
		return -1;
	return total + size;
}

// TODO: Need a nbt_dump_to_buffer method so we don't allocate memory or risk
// failure here. Our own dest buffer should be big enough based on size_
// functions so there is really no excuse for an encode to fail.
char *enc_nbt(char *dest, nbt_node *source) {
	struct buffer b = nbt_dump_binary(source);
	memcpy(dest, b.data, b.len);
	free(b.data);
	return dest + b.len;
}

char *dec_nbt(nbt_node **dest, char *source) {
	// nbt_parse2 is a stupid hack I kludged in order to pass char** to cNBT and
	// advance our source pointer appropriately. Also, max_len shouldn't be
	// a thing since we require the nbt to be walked before parsing.
	if(!(*dest = nbt_parse2(&source, NO_OVERFLOW)))
		return NULL;
	return source;
}

int walk_optnbt(char *source, size_t max_len) {
	if(!max_len)
		return -1;
	if(*source != TAG_COMPOUND)
		return sizeof(*source);
	return walk_nbt(source, max_len);
}

size_t size_optnbt(nbt_node *nbt) {
	if(!nbt)
		return sizeof(char);
	return size_nbt(nbt);
}

char *enc_optnbt(char *dest, nbt_node *source) {
	if(!source)
		return enc_byte(dest, 0);
	return enc_nbt(dest, source);
}

char *dec_optnbt(nbt_node **dest, char *source) {
	if(*source != TAG_COMPOUND) {
		*dest = NULL;
		return ++source;
	}
	return dec_nbt(dest, source);
}

// Inventory slot
int walk_slot(char *source, size_t max_len) {
	mc_slot slot;
	if(max_len < sizeof(slot.present))
		return -1;
	source = dec_byte((uint8_t *) &slot.present, source);
	size_t size = sizeof(slot.present);
	if(!slot.present)
		return size;
	int ret = walk_varint(source, --max_len);
	if(ret < 0)
		return -1;
	if(max_len -= ret < sizeof(slot.count))
		return -1;
	max_len -= sizeof(slot.count);
	size += ret + sizeof(slot.count);
	source += ret + sizeof(slot.count);
	if(*source != TAG_COMPOUND)
		return ++size;
	ret = walk_nbt(source, max_len);
	if(ret < 0)
		return -1;
	return size + ret;
}

size_t size_slot(mc_slot slot) {
	if(!slot.present)
		return sizeof(slot.present);
	size_t size = sizeof(slot.present) + sizeof(slot.count);
	size += size_varint(slot.id);
	if(slot.nbt)
		size += size_nbt(slot.nbt);
	return size;
}

// Just like varint/long, we assume you're being a good citizen and using the
// size function to ensure no buffer overflows.
char *enc_slot(char *dest, mc_slot source) {
	dest = enc_byte(dest, (uint8_t) source.present);
	if(!source.present)
		return dest;
	dest = enc_varint(dest, (uint32_t) source.id);
	dest = enc_byte(dest, source.count);
	if(!source.nbt)
		return enc_byte(dest, 0);
	return enc_nbt(dest, source.nbt);
}

// dec_nbt allocates memory, this can fail and return NULL
char *dec_slot(mc_slot *dest, char *source) {
	source = dec_byte((uint8_t *)&dest->present, source);
	if(!dest->present)
		return source;
	source = dec_varint(&dest->id, source);
	source = dec_byte(&dest->count, source);
	if(*source != TAG_COMPOUND) {
		dest->nbt = NULL;
		return ++source;
	}
	return dec_nbt(&dest->nbt, source);
}

void free_slot(mc_slot slot) {
	nbt_free(slot.nbt);
}

// Varint prefixed array of slots
int walk_ingredient(char *source, size_t max_len) {
	int ret = walk_varint(source, max_len);
	if(ret < 0)
		return ret;
	int size = ret;
	max_len -= ret;
	int32_t len;
	source = dec_varint(&len, source);
	for(int i = 0; i < len; i++, size += ret, max_len -= ret) {
		if((ret = walk_slot(source, max_len)) < 0)
			return ret;
	}
	return size;
}

size_t size_ingredient(mc_ingredient ingredient) {
	size_t size = size_varint(ingredient.count);
	for(int i = 0; i < ingredient.count; i++) {
		size += size_slot(ingredient.items[i]);
	}
	return size;
}

char *enc_ingredient(char *dest, mc_ingredient source) {
	dest = enc_varint(dest, source.count);
	for(int i = 0; i < source.count; i++) {
		dest = enc_slot(dest, source.items[i]);
	}
	return dest;
}

char *dec_ingredient(mc_ingredient *dest, char *source) {
	source = dec_varint(&dest->count, source);
	for(int i = 0; i < dest->count; i++) {
		if(!(source = dec_slot(&dest->items[i], source)))
			return NULL;
	}
	return source;
}

void free_ingredient(mc_ingredient ingredient) {
	for(int i = 0; i < ingredient.count; i++) {
		free_slot(ingredient.items[i]);
	}
	free(ingredient.items);
}

int walk_smelting(char *source, size_t max_len) {
	int ret = walk_string(source, max_len);
	if(ret < 0)
		return ret;
	int size = ret;
	source += ret;
	max_len -= ret;
	if(ret = walk_ingredient(source, max_len) < 0)
		return ret;
	size += ret;
	source += ret;
	max_len -= ret;
	if(ret = walk_slot(source, max_len) < 0)
		return ret;
	size += ret;
	source += ret;
	max_len -= ret;
	if(max_len < ssizeof(mc_smelting, experience))
		return -1;
	size += ret;
	source += ssizeof(mc_smelting, experience);
	max_len -= ssizeof(mc_smelting, experience);
	if(ret = walk_varint(source, max_len) < 0)
		return ret;
	return size + ret;
}

size_t size_smelting(mc_smelting smelting) {
	size_t total = size_string(smelting.group);
	total += size_ingredient(smelting.ingredient);
	total += size_slot(smelting.result);
	total += sizeof(smelting.experience);
	total += size_varint(smelting.cooking_time);
	return total;
}

char *enc_smelting(char *dest, mc_smelting source) {
	dest = enc_string(dest, source.group);
	dest = enc_ingredient(dest, source.ingredient);
	dest = enc_slot(dest, source.result);
	dest = enc_bef32(dest, source.experience);
	return enc_varint(dest, source.cooking_time);
}

char *dec_smelting(mc_smelting *dest, char *source) {
	source = dec_string(&dest->group, source);
	source = dec_ingredient(&dest->ingredient, source);
	source = dec_slot(&dest->result, source);
	source = dec_bef32(&dest->experience, source);
	return dec_varint(&dest->cooking_time, source);
}

void free_smelting(mc_smelting smelting) {
	free_string(smelting.group);
	free_ingredient(smelting.ingredient);
	free_slot(smelting.result);
}

int walk_particledata(char *source, size_t max_len, particle_type type) {
	int ret = walk_varint(source, max_len);
	if(ret < 0)
		return -1;
	int size = ret;
	source += ret;
	max_len -= ret;
	switch(type) {
		case particle_block:
		case particle_falling_dust:
			if(ret = walk_varint(source, max_len) < 0)
				return ret;
			size += ret;
			break;
		case particle_dust:
			if(max_len < sizeof(float) * 4)
				return -1;
			size += sizeof(float) * 4;
		case particle_item:
			if(ret = walk_slot(source, max_len) < 0)
				return ret;
			size += ret;
	}
	return size;
}

size_t size_particledata(mc_particle particle) {
	switch(particle.type) {
		case particle_block:
		case particle_falling_dust:
			return size_varint(particle.block_state);
		case particle_dust:
			return sizeof(float) * 4;
		case particle_item:
			return size_slot(particle.item);
		default:
			return 0;
	}
}

char *enc_particledata(char *dest, mc_particle source) {
	switch(source.type) {
		case particle_block:
		case particle_falling_dust:
			return enc_varint(dest, source.block_state);
			break;
		case particle_dust:
			dest = enc_bef32(dest, source.red);
			dest = enc_bef32(dest, source.green);
			dest = enc_bef32(dest, source.blue);
			return enc_bef32(dest, source.scale);
			break;
		case particle_item:
			return enc_slot(dest, source.item);
			break;
		default:
			return dest;
	}
}

char *dec_particledata(mc_particle *dest, char *source, particle_type type) {
	dest->type = type;
	switch(type) {
		case particle_block:
		case particle_falling_dust:
			return dec_varint(&dest->block_state, source);
			break;
		case particle_dust:
			source = dec_bef32(&dest->red, source);
			source = dec_bef32(&dest->green, source);
			source = dec_bef32(&dest->blue, source);
			return dec_bef32(&dest->scale, source);
			break;
		case particle_item:
			return dec_slot(&dest->item, source);
			break;
		default:
			return source;
	}
}

void free_particledata(mc_particle particle) {
	if(particle.type == particle_item)
		free_slot(particle.item);
}


// ToDo: Everything about metadata is a fucking mess and needs to be rebuilt
// from the ground up. Metadata alone makes the whole "walk/decode" paradigm
// not worth it. Serious thought should be given to a better buffer system that
// can side-step this insanity. Raw char * is just asking for pain.
int walk_metadata(char *source, size_t max_len) {
	if(!max_len)
		return -1;
	int total = 0;
	for(int size, ret; *(unsigned char *) source != 0xFF;
			 source += size, max_len -= size, total += size) {
		total++;
		if((ret = walk_varint(++source, --max_len)) < 0)
			return ret;
		max_len -= ret;
		total += ret;
		int32_t type;
		source = dec_varint(&type, source);
		switch(type) {
			case meta_byte:
			case meta_boolean:
			case meta_direction:
				size = sizeof(char);
				break;
			case meta_varint:
			case meta_optblockid:
			case meta_pose:
				if((size = walk_varint(source, max_len)) < 0)
					return size;
				break;
			case meta_float:
				size = sizeof(float);
				break;
			case meta_string:
			case meta_chat:
				if((size = walk_string(source, max_len)) < 0)
					return size;
				break;
			case meta_optchat:
				size = sizeof(char);
				if(*source) {
					if((ret = walk_string(source + 1, max_len - 1)) < 0)
						return ret;
					size += ret;
				}
				break;
			case meta_slot:
				if((size = walk_slot(source, max_len)) < 0)
					return size;
				break;
			case meta_rotation:
				size = sizeof(float) * 3;
				break;
			case meta_position:
				size = sizeof(uint64_t);
				break;
			case meta_optposition:
				size = sizeof(char);
				if(*source)
					size += sizeof(uint64_t);
				break;
			case meta_optuuid:
				size = sizeof(char);
				if(*source)
					size += sizeof(uint64_t) * 2;
				break;
			case meta_nbt:
				if((size = walk_nbt(source, max_len)) < 0)
					return size;
				break;
			case meta_particle:
				if((size = walk_particle(source, max_len)) < 0)
					return size;
				break;
			case meta_villagerdata:
				size = 0;
				for(size_t j = 0; j < 3; j++) {
					if((ret = walk_varint(source, max_len)) < 0)
						return ret;
					source += ret;
					max_len -= ret;
					total += ret;
				}
				break;
			case meta_optvarint:
				size = sizeof(char);
				if(*source) {
					if((ret = walk_varint(source + 1, max_len - 1)) < 0)
						return ret;
					size += ret;
				}
				break;
			default:
				return -1;
				break;
		}
		// Need to read at least one more byte to get the meta close tag 0xFF
		// Therefore we use <= here instead of just <
		if(max_len <= (size_t) size)
			return -1;
	}
	return ++total;
}

// TODO: counting metatags takes almost as long as decoding them
// we could write a fast_decode that just groups those two
size_t count_metatags(char *source) {
	size_t count = 0;
	for(int32_t type; *(unsigned char *) source != 0xFF; count++) {
		source = dec_varint(&type, ++source);
		switch(type) {
			case meta_byte:
			case meta_boolean:
			case meta_direction:
				source += sizeof(char);
				break;
			case meta_varint:
			case meta_optblockid:
			case meta_pose:
				source += walk_varint(source, NO_OVERFLOW);
				break;
			case meta_float:
				source += sizeof(float);
				break;
			case meta_string:
			case meta_chat:
				source += walk_string(source, NO_OVERFLOW);
				break;
			case meta_optchat:
				if(*source++)
					source += walk_string(source, NO_OVERFLOW);
				break;
			case meta_slot:
				source += walk_slot(source, NO_OVERFLOW);
				break;
			case meta_rotation:
				source += sizeof(float) * 3;
				break;
			case meta_position:
				source += sizeof(uint64_t);
				break;
			case meta_optposition:
				if(*source++)
					source += sizeof(uint64_t);
				break;
			case meta_optuuid:
				if(*source++)
					source += sizeof(uint64_t) * 2;
				break;
			case meta_nbt:
				source += walk_nbt(source, NO_OVERFLOW);
				break;
			case meta_particle:
				source += walk_particle(source, NO_OVERFLOW);
				break;
			case meta_villagerdata:
				for(size_t j = 0; j < 3; j++)
					source += walk_varint(source, NO_OVERFLOW);
				break;
			case meta_optvarint:
				if(*source++)
					source += walk_varint(source, NO_OVERFLOW);
				break;
			default:
				//ToDo: This probably isn't right
				return 0;
				break;
		}
	}
	return count;
}

size_t size_metadata(mc_metadata metadata) {
	size_t size = 0;
	for(size_t i = 0; i < metadata.len; i++) {
		size += sizeof(metadata.tags[0].index);
		size += size_varint(metadata.tags[i].type);
		switch(metadata.tags[i].type) {
			case meta_byte:
			case meta_boolean:
			case meta_direction:
				size += sizeof(char);
				break;
			case meta_varint:
			case meta_optblockid:
			case meta_pose:
				size += size_varint(metadata.tags[i].varint);
				break;
			case meta_float:
				size += sizeof(float);
				break;
			case meta_string:
			case meta_chat:
				size += size_string(metadata.tags[i].string);
				break;
			case meta_optchat:
				size += sizeof(char);
				if(metadata.tags[i].opt)
					size += size_string(metadata.tags[i].string);
				break;
			case meta_slot:
				size += size_slot(metadata.tags[i].slot);
				break;
			case meta_rotation:
				size += sizeof(float) * 3;
				break;
			case meta_position:
				size += sizeof(uint64_t);
				break;
			case meta_optposition:
				size += sizeof(char);
				if(metadata.tags[i].opt)
					size += sizeof(uint64_t);
				break;
			case meta_optuuid:
				size += sizeof(char);
				if(metadata.tags[i].opt)
					size += sizeof(uint64_t) * 2;
				break;
			case meta_nbt:
				size += size_nbt(metadata.tags[i].nbt);
				break;
			case meta_particle:
				size += size_particle(metadata.tags[i].particle);
				break;
			case meta_villagerdata:
				for(size_t j = 0; j < 3; j++)
					size += size_varint(metadata.tags[i].villagerdata[j]);
				break;
			case meta_optvarint:
				size += sizeof(char);
				if(metadata.tags[i].opt)
					size += size_varint(metadata.tags[i].varint);
				break;
			default:
				//See above default case
				return 0;
				break;
		}
	}
	return ++size;
}

char *enc_metadata(char *dest, mc_metadata source) {
	for(size_t i = 0; i < source.len; i++) {
		dest = enc_byte(dest, source.tags[i].index);
		dest = enc_varint(dest, source.tags[i].type);
		switch(source.tags[i].type) {
			case meta_byte:
			case meta_boolean:
			case meta_direction:
				dest = enc_byte(dest, source.tags[i].b);
				break;
			case meta_varint:
			case meta_optblockid:
			case meta_pose:
				dest = enc_varint(dest, source.tags[i].varint);
				break;
			case meta_float:
				dest = enc_bef32(dest, source.tags[i].f);
				break;
			case meta_string:
			case meta_chat:
				dest = enc_string(dest, source.tags[i].string);
				break;
			case meta_optchat:
				dest = enc_byte(dest, source.tags[i].opt);
				if(source.tags[i].opt)
					dest = enc_string(dest, source.tags[i].string);
				break;
			case meta_slot:
				dest = enc_slot(dest, source.tags[i].slot);
				break;
			case meta_rotation:
				dest = enc_bef32(dest, source.tags[i].rot.x);
				dest = enc_bef32(dest, source.tags[i].rot.y);
				dest = enc_bef32(dest, source.tags[i].rot.z);
				break;
			case meta_position:
				dest = enc_position(dest, source.tags[i].pos);
				break;
			case meta_optposition:
				dest = enc_byte(dest, source.tags[i].opt);
				if(source.tags[i].opt)
					dest = enc_position(dest, source.tags[i].pos);
				break;
			case meta_optuuid:
				dest = enc_byte(dest, source.tags[i].opt);
				if(source.tags[i].opt)
					dest = enc_uuid(dest, source.tags[i].uuid);
				break;
			case meta_nbt:
				dest = enc_nbt(dest, source.tags[i].nbt);
				break;
			case meta_particle:
				dest = enc_particle(dest, source.tags[i].particle);
				break;
			case meta_villagerdata:
				for(size_t j = 0; j < 3; j++)
					dest = enc_varint(dest, source.tags[i].villagerdata[j]);
				break;
			case meta_optvarint:
				dest = enc_byte(dest, source.tags[i].opt);
				if(source.tags[i].opt)
					dest = enc_varint(dest, source.tags[i].varint);
				break;
		}
	}
	return enc_byte(dest, 0);
}

char *dec_metadata(mc_metadata *dest, char *source) {
	size_t len = count_metatags(source);
	dest->len = len;
	if(!(dest->tags = malloc(len * sizeof(mc_metatag))))
		return NULL;
	for(size_t i = 0; i < len; i++) {
		source = dec_byte(&dest->tags[i].index, source);
		source = dec_varint(&dest->tags[i].type, source);
		switch(dest->tags[i].type) {
			case meta_byte:
			case meta_boolean:
			case meta_direction:
				source = dec_byte((uint8_t *)&dest->tags[i].b, source);
				break;
			case meta_varint:
			case meta_optblockid:
			case meta_pose:
				source = dec_varint(&dest->tags[i].varint, source);
				break;
			case meta_float:
				source = dec_bef32(&dest->tags[i].f, source);
				break;
			case meta_string:
			case meta_chat:
				source = dec_string(&dest->tags[i].string, source);
				break;
			case meta_optchat:
				source = dec_byte((uint8_t *)&dest->tags[i].opt, source);
				if(dest->tags[i].opt)
					source = dec_string(&dest->tags[i].string, source);
				break;
			case meta_slot:
				source = dec_slot(&dest->tags[i].slot, source);
				break;
			case meta_rotation:
				source = dec_bef32(&dest->tags[i].rot.x, source);
				source = dec_bef32(&dest->tags[i].rot.y, source);
				source = dec_bef32(&dest->tags[i].rot.z, source);
				break;
			case meta_position:
				source = dec_position(&dest->tags[i].pos, source);
				break;
			case meta_optposition:
				source = dec_byte((uint8_t *)&dest->tags[i].opt, source);
				if(dest->tags[i].opt)
					source = dec_position(&dest->tags[i].pos, source);
				break;
			case meta_optuuid:
				source = dec_byte((uint8_t *)&dest->tags[i].opt, source);
				if(dest->tags[i].opt)
					source = dec_uuid(&dest->tags[i].uuid, source);
				break;
			case meta_nbt:
				source = dec_nbt(&dest->tags[i].nbt, source);
				break;
			case meta_particle:
				source = dec_particle(&dest->tags[i].particle, source);
				break;
			case meta_villagerdata:
				for(size_t j = 0; j < 3; j++)
					source = dec_varint(&dest->tags[i].villagerdata[j], source);
				break;
			case meta_optvarint:
				source = dec_byte((uint8_t *) &dest->tags[i].opt, source);
				if(dest->tags[i].opt)
					source = dec_varint(&dest->tags[i].varint, source);
				break;
		}
	}
	return ++source;
}

void free_metadata(mc_metadata metadata) {
	for(size_t i = 0; i < metadata.len; i++) {
		switch(metadata.tags[i].type) {
		case meta_string:
		case meta_chat:
			sdsfree(metadata.tags[i].string);
			break;
		case meta_optchat:
			if(metadata.tags[i].opt) {
				sdsfree(metadata.tags[i].string);
			}
			break;
		case meta_slot:
			free_slot(metadata.tags[i].slot);
			break;
		case meta_nbt:
			free_nbt(metadata.tags[i].nbt);
			break;
		case meta_particle:
			free_particle(metadata.tags[i].particle);
			break;
		default:
			break;
		}
	}
}

int walk_itemtag_array(char *source, size_t max_len) {
	if(!max_len)
		return -1;
	int ret = walk_varint(source, max_len);
	if(ret < 0)
		return ret;
	int size = ret;
	max_len -= ret;
	int32_t varint;
	source = dec_varint(&varint, source);
	for(size_t i = 0, j = varint; i < j; i++) {
		if((ret = walk_string(source, max_len)) < 0)
			return ret;
		max_len -= ret;
		source += ret;
		size += ret;
		if((ret = walk_varint(source, max_len)) < 0)
			return ret;
		max_len -= ret;
		size += ret;
		source = dec_varint(&varint, source);
		for(int k = 0; k < varint; k++, size += ret, max_len -= ret) {
			if((ret = walk_varint(source, max_len)) < 0)
				return ret;
		}
	}
	return size;
}

size_t size_itemtag_array(mc_itemtag_array itemtag_array) {
	size_t size = size_varint(itemtag_array.len);
	for(int i = 0; i < itemtag_array.len; i++) {
		size += size_string(itemtag_array.tags[i].name);
		size += size_varint(itemtag_array.tags[i].len);
		for(int j = 0; j < itemtag_array.tags[i].len; j++) {
			size += size_varint(itemtag_array.tags[i].entries[j]);
		}
	}
	return size;
}

char *enc_itemtag_array(char *dest, mc_itemtag_array source) {
	dest = enc_varint(dest, source.len);
	for(int i = 0; i < source.len; i++) {
		dest = enc_string(dest, source.tags[i].name);
		dest = enc_varint(dest, source.tags[i].len);
		for(int j = 0; j < source.tags[i].len; j++) {
			dest = enc_varint(dest, source.tags[i].entries[j]);
		}
	}
	return dest;
}

char *dec_itemtag_array(mc_itemtag_array *dest, char *source) {
	source = dec_varint(&dest->len, source);
	if(!(dest->tags = malloc(dest->len * sizeof(*dest->tags))))
		return NULL;
	for(int i = 0; i < dest->len; i++) {
		source = dec_string(&dest->tags[i].name, source);
		source = dec_varint(&dest->tags[i].len, source);
		if(!(dest->tags[i].entries =
							malloc(dest->tags[i].len * sizeof(*dest->tags[i].entries))))
			return NULL;
		for(int j = 0; j < dest->tags[i].len; j++) {
			source = dec_varint(&dest->tags[i].entries[j], source);
		}
	}
	return source;
}

void free_itemtag_array(mc_itemtag_array array) {
	for(int i = 0; i < array.len; i++) {
		sdsfree(array.tags[i].name);
		free(array.tags[i].entries);
	}
	free(array.tags);
}
