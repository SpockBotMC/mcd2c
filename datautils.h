#ifndef DATAUTILS_H
#define DATAUTILS_H

#include <stdint.h>
#include "sds.h"
#include "cNBT/nbt.h"

//Get the size of a member of a structure without instantiating it
#define ssizeof(X, Y) sizeof(((X*)0)->Y)

typedef struct {
  size_t len;
  char *base;
} mc_buffer;

//ProtoDef Numeric Type
char *enc_byte(char *dest, uint8_t source);
char *dec_byte(uint8_t *dest, char *source);
char *enc_be16(char *dest, uint16_t source);
char *dec_be16(uint16_t *dest, char *source);
char *enc_be32(char *dest, uint32_t source);
char *dec_be32(uint32_t *dest, char *source);
char *enc_be64(char *dest, uint64_t source);
char *dec_be64(uint64_t *dest, char *source);
char *enc_le16(char *dest, uint16_t source);
char *dec_le16(uint16_t *dest, char *source);
char *enc_le32(char *dest, uint32_t source);
char *dec_le32(uint32_t *dest, char *source);
char *enc_le64(char *dest, uint64_t source);
char *dec_le64(uint64_t *dest, char *source);
char *enc_bef32(char *dest, float source);
char *dec_bef32(float *dest, char *source);
char *enc_bef64(char *dest, double source);
char *dec_bef64(double *dest, char *source);
char *enc_lef32(char *dest, float source);
char *dec_lef32(float *dest, char *source);
char *enc_lef64(char *dest, double source);
char *dec_lef64(double *dest, char *source);

char *enc_buffer(char *dest, mc_buffer source);
char *dec_buffer(mc_buffer *dest, char *source, size_t len);
void free_buffer(mc_buffer buffer);

enum {
  varnum_invalid = -1,
  varnum_overrun = -2,
} varnum_errors;

size_t size_varint(uint32_t varint);
int walk_varint(char *source, size_t max_len);
char *enc_varint(char *dest, uint32_t source);
char *dec_varint(int32_t *dest, char *source);

size_t size_varlong(uint64_t varint);
int walk_varlong(char *source, size_t max_len);
char *enc_varlong(char *dest, uint64_t source);
char *dec_varlong(int64_t *dest, char *source);

size_t size_string(sds string);
int walk_string(char *source, size_t max_len);
char *enc_string(char *dest, sds source);
char *dec_string(sds *dest, char *source);
#define free_string(x) sdsfree(x)

//Big Endian 128-bit uint
typedef struct {
  uint64_t msb;
  uint64_t lsb;
} mc_uuid;

char *enc_uuid(char *dest, mc_uuid source);
char *dec_uuid(mc_uuid *dest, char *source);

//From MSB to LSB x: 26-bits, y: 12-bits, z: 26-bits
//each is an independent signed 2-complement integer
typedef struct {
  int32_t x;
  int32_t y;
  int32_t z;
} mc_position;

char *enc_position(char *dest, mc_position source);
char *dec_position(mc_position *dest, char *source);

size_t size_unnamed_nbt(nbt_node *node);
size_t size_nbt_list(nbt_node *node);
size_t size_nbt_compound(nbt_node *node);
size_t size_unnamed_nbt(nbt_node *node);
size_t size_nbt(nbt_node *nbt);
int walk_unnamed_nbt(char *source, nbt_type type, size_t max_len);
int walk_nbt_string(char *source, size_t max_len);
int walk_nbt_array(char *source, size_t max_len, size_t type_len);
int walk_nbt_list(char *source, size_t max_len);
int walk_nbt_compound(char *source, size_t max_len);
int walk_unnamed_nbt(char *source, nbt_type type, size_t max_len);
int walk_nbt(char *source, size_t max_len);
char *enc_nbt(char *dest, nbt_node *source);
char *dec_nbt(nbt_node **dest, char *source);
#define free_nbt(x) nbt_free(x)

int walk_optnbt(char *source, size_t max_len);
size_t size_optnbt(nbt_node *nbt);
char *enc_optnbt(char *dest, nbt_node *source);
char *dec_optnbt(nbt_node **dest, char *source);
#define free_optnbt(x) nbt_free(x)

//Inventory slot
typedef struct {
  char present;
  int32_t id;
  uint8_t count;
  nbt_node *nbt;
} mc_slot;

int walk_slot(char *source, size_t max_len);
size_t size_slot(mc_slot slot);
char *enc_slot(char *dest, mc_slot source);
char *dec_slot(mc_slot *dest, char *source);
void free_slot(mc_slot slot);

//Varint prefixed array of slots
typedef struct {
  int32_t count;
  mc_slot *items;
} mc_ingredient;

int walk_ingredient(char *source, size_t max_len);
size_t size_ingredient(mc_ingredient ingredient);
char *enc_ingredient(char *dest, mc_ingredient source);
char *dec_ingredient(mc_ingredient *dest, char *source);
void free_ingredient(mc_ingredient ingredient);

typedef struct {
  sds group;
  mc_ingredient ingredient;
  mc_slot result;
  float experience;
  int32_t cooking_time;
} mc_smelting;

int walk_smelting(char *source, size_t max_len);
size_t size_smelting(mc_smelting smelting);
char *enc_smelting(char *dest, mc_smelting source);
char *dec_smelting(mc_smelting *dest, char *source);
void free_smelting(mc_smelting smelting);

typedef enum {
  particle_ambient_entity_effect,
  particle_angry_villager,
  particle_barrier,
  particle_block,
  particle_bubble,
  particle_cloud,
  particle_crit,
  particle_damage_indicator,
  particle_dragon_breath,
  particle_dripping_lava,
  particle_dripping_water,
  particle_dust,
  particle_effect,
  particle_elder_guardian,
  particle_enchanted_hit,
  particle_enchant,
  particle_end_rod,
  particle_entity_effect,
  particle_explosion_emitter,
  particle_explosion,
  particle_falling_dust,
  particle_firework,
  particle_fishing,
  particle_flame,
  particle_happy_villager,
  particle_heart,
  particle_instant_effect,
  particle_item,
  particle_item_slime,
  particle_item_snowball,
  particle_large_smoke,
  particle_lava,
  particle_mycelium,
  particle_note,
  particle_poof,
  particle_portal,
  particle_rain,
  particle_smoke,
  particle_spit,
  particle_squid_ink,
  particle_sweep_attack,
  particle_totem_of_undying,
  particle_underwater,
  particle_splash,
  particle_witch,
  particle_bubble_pop,
  particle_current_down,
  particle_bubble_column_up,
  particle_nautilus,
  particle_dolphin
} particle_type;

typedef struct {
  int32_t type;
  union {
    int32_t block_state;
    struct {
      float red;
      float green;
      float blue;
      float scale;
    };
    mc_slot item;
  };
} mc_particle;

int walk_particledata(char *source, size_t max_len, particle_type type);
size_t size_particledata(mc_particle particle);
char *enc_particledata(char *dest, mc_particle source);
char *dec_particledata(mc_particle *dest, char *source, particle_type type);
void free_particledata(mc_particle particle);

int walk_particle(char *source, size_t max_len);
size_t size_particle(mc_particle particle);
char *enc_particle(char *dest, mc_particle source);
char *dec_particle(mc_particle *dest, char *source);
#define free_particle free_particledata


typedef enum {
  meta_byte,
  meta_varint,
  meta_float,
  meta_string,
  meta_chat,
  meta_optchat,
  meta_slot,
  meta_boolean,
  meta_rotation,
  meta_position,
  meta_optposition,
  meta_direction,
  meta_optuuid,
  meta_optblockid,
  meta_nbt,
  meta_particle,
  meta_villagerdata,
  meta_optvarint,
  meta_pose
} meta_type;

//Just a bitch of a type really
typedef struct {
  uint8_t index;
  int32_t type;
  char opt;
  union {
    int8_t b;
    int32_t varint;
    float f;
    sds string;
    mc_slot slot;
    struct {
      float x;
      float y;
      float z;
    } rot;
    mc_position pos;
    mc_uuid uuid;
    nbt_node *nbt;
    mc_particle particle;
    int32_t villagerdata[3];
  };
} mc_metatag;

typedef struct {
  size_t len;
  mc_metatag *tags;
} mc_metadata;

size_t count_metatags(char *source);
int walk_metadata(char *source, size_t max_len);
size_t size_metadata(mc_metadata metadata);
char *enc_metadata(char *dest, mc_metadata source);
char *dec_metadata(mc_metadata *dest, char *source);
void free_metadata(mc_metadata metadata);

typedef struct {
  sds name;
  int32_t len;
  int32_t *entries;
} mc_itemtag;

typedef struct {
 int32_t len;
 mc_itemtag *tags;
} mc_itemtag_array;

int walk_itemtag_array(char *source, size_t max_len);
size_t size_itemtag_array(mc_itemtag_array itemtag_array);
char *enc_itemtag_array(char *dest, mc_itemtag_array source);
char *dec_itemtag_array(mc_itemtag_array *dest, char *source);
void free_itemtag_array(mc_itemtag_array array);

typedef struct {
  int id;
  size_t len;
  void *data;
} mc_packet;

#endif
