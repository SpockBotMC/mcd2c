# This is an old version of mcd2c kept around for reference only while I get
# mcd2c_2 working. No development should be done on this file

import cfile as c
import minecraft_data
import re

#This is not a real compiler, there is no IR or anything. Just walks the
#minecraft_data protocol tree and magics up some C

#All varints are varlongs until this gets fixed
#https://github.com/PrismarineJS/minecraft-data/issues/119

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')
def to_snake_case(name):
    if name is None: return None
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()

proto_states = "handshaking", "login", "status", "play"
directions = "toClient", "toServer"

type_name_map = {
    'bool': 'uint8_t',
    'i8':   'int8_t',
    'u8':   'uint8_t',
    'li8':  'int8_t',
    'lu8':  'uint8_t',
    'i16':  'int16_t',
    'u16':  'uint16_t',
    'li16': 'int16_t',
    'lu16': 'uint16_t',
    'i32':  'int32_t',
    'u32':  'uint32_t',
    'li32': 'int32_t',
    'lu32': 'uint32_t',
    'i64':  'int64_t',
    'u64':  'uint64_t',
    'li64': 'int64_t',
    'lu64': 'uint64_t',
    'f32':  'float',
    'lf32': 'float',
    'f64':  'double',
    'lf64': 'double',
    'uuid': 'mc_uuid',
    'position': 'mc_position',
    'varint': 'int64_t', #change when 119 is fixed
    'varlong': 'int64_t',
    'string': 'sds',
    'slot': 'mc_slot',
    'particle': 'mc_particle',
    'ingredient': 'mc_ingredient',
    'nbt': 'nbt_node *',
    'optionalnbt': 'nbt_node *',
    'buffer': 'mc_buffer',
    'restbuffer': 'mc_buffer',
    'entitymetadata': 'mc_metadata',
    'tags': 'mc_itemtag_array',
    'particledata': 'mc_particle',
}

numeric_type_map = {
    'bool':  'byte',
    'i8':    'byte',
    'u8':    'byte',
    'li8':   'byte',
    'lu8':   'byte',
    'i16':   'be16',
    'u16':   'be16',
    'li16':  'le16',
    'lu16':  'le16',
    'i32':   'be32',
    'u32':   'be32',
    'li32':  'le32',
    'lu32':  'le32',
    'i64':   'be64',
    'u64':   'be64',
    'li64':  'le64',
    'lu64':  'le64',
    'f32':  'bef32',
    'lf32': 'lef32',
    'f64':  'bef64',
    'lf64': 'lef64',
    'uuid': 'uuid', #uuids are basically numerics
    'position': 'position', #so are positions
}

numeric_sizes = {
    'byte': 1,
    'be16': 2,
    'le16': 2,
    'be32': 4,
    'le32': 4,
    'be64': 8,
    'le64': 8,
    'bef32': 4,
    'lef32': 4,
    'bef64': 8,
    'lef64': 8,
    'uuid': 16,
    'position': 8,
}

complex_type_map = {
    'varint': 'varlong', #change when 119 is fixed
    'varlong': 'varlong',
    'string': 'string',
    'slot': 'slot',
    'particle': 'particle',
    'ingredient': 'ingredient',
    'nbt': 'nbt',
    'optionalnbt': 'optnbt',
    'entitymetadata': 'metadata',
    'tags': 'itemtag_array',
}

malloc_types = {
    'string': 'string',
    'slot': 'slot',
    'particle': 'particle',
    'ingredient': 'ingredient',
    'nbt': 'nbt',
    'optionalnbt': 'optnbt',
    'entitymetadata': 'metadata',
    'tags': 'itemtag_array',
    'restbuffer': 'buffer',
    'buffer': 'buffer'
}
cast_map = {
    'i8':   'uint8_t',
    'li8':  'uint8_t',
    'i16':  'uint16_t',
    'li16': 'uint16_t',
    'i32':  'uint32_t',
    'li32': 'uint32_t',
    'i64':  'uint64_t',
    'li64': 'uint64_t',
}

def decode_generic(type, location, assign = True):
    at = 'source = ' if assign else ''
    return c.line(at + str(c.fcall('dec_'+type).add_param(location).add_param('source')))

def container_size(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def container_walk(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def container_enc(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def container_dec(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def container_struct(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def handle_container(field, op):
    return {
        'size': container_size,
        'walk': container_walk,
        'enc': container_enc,
        'dec': container_dec,
        'struct': container_struct,
    }[op](field)

def buffer_size(field):
    ret = c.sequence()
    len_field = 'packet.' + field.name + '.len'
    ct = field.custom_payload['countType']
    if ct == 'varint' or ct == 'varlong':
        ct = 'varlong' #Remove when 119 is fixed
        size = c.fcall('size_' + ct).add_param(len_field)
    else:
        size = numeric_sizes[numeric_type_map[field.type]]
    ret.appstat('size += ' + str(size) + ' + ' + len_field)
    return ret;

def buffer_walk(field):
    len_name = field.name + '_len'
    ct = field.custom_payload['countType']
    if ct == 'varint':
        ct = 'varlong' #Remove when 119 is fixed
    ret = gen_walker_inner((_field(ct, field.packet, len_name, None, False, True),))
    ret.appstat('if (max_len < (size_t) '+ len_name + ') return -1')
    ret.appstat('size += ' + len_name)
    if not field.final:
        ret.appstat('source += ' + len_name)
        ret.appstat('max_len -= sizeof(' + len_name +') + ' + len_name)
    return ret;

def buffer_enc(field):
    ret = c.sequence()
    ct = field.custom_payload['countType']
    len_name = 'source.' + field.name + '.len'
    if ct == 'varint' or ct == 'varlong':
        ct = 'varlong' #Remove when 119 is fixed
        ret.appstat('dest = ' +
            str(c.fcall('enc_' + ct).add_param('dest').add_param(len_name))
        )
    else:
        ret.appstat('dest = ' + str(c.fcall(
            'enc_' + numeric_type_map[ct]
        ).add_param('dest').add_param(len_name)))
    ret.appstat(str(c.fcall('memcpy').add_param('dest').add_param(
        'source.' + field.name + '.data').add_param(len_name)
    ))
    ret.appstat('dest += ' + len_name)
    return ret;

def buffer_dec(field):
    ret = c.sequence()
    ct = field.custom_payload['countType']
    len_name = 'dest->' + field.name + '.len'
    buf_name = 'dest->' + field.name + '.data'
    if ct == 'varint' or ct == 'varlong':
        ct = 'varlong' #Remove when 119 is fixed
        ret.appstat(decode_generic(ct, '(int64_t *) &' + len_name))
    else:
        ret.appstat(decode_generic(numeric_type_map[ct], '&' + len_name))
    ret.appstat('if(!(' + buf_name + ' = ' +
        str(c.fcall('malloc').add_param(len_name)) + ')) return NULL'
    )
    ret.appstat(str(c.fcall('memcpy').add_param(buf_name).add_param(
        'source').add_param(len_name)
    ))
    ret.appstat('dest += ' + len_name)
    return ret;

#In practice handled by type_name_map and gen_packet_structure, but implemented
#just in case I change that.
def buffer_struct(field):
    return c.statement(c.variable(field.name, 'mc_buffer'))

def handle_buffer(field, op):
    return {
        'size': buffer_size,
        'walk': buffer_walk,
        'enc': buffer_enc,
        'dec': buffer_dec,
        'struct': buffer_struct,
    }[op](field)

def get_bitfield_size(field):
    total = 0
    for segment in field.custom_payload:
        total += segment['size']
    return total//8

#bitfield size/walk is handled by the size preprocessor, in practice these
#are never called
def bitfield_size(field):
    return c.statement('size += ' + str(get_bitfield_size(field)))

def bitfield_walk(field):
    size = str(get_bitfield_size(field))
    return c.sequence().appstat('size += ' + size).appstat('source += ' + size
    ).appstat('max_len -= ' + size)

def bitfield_enc(field):
    ret = c.sequence()
    size = get_bitfield_size(field)
    type = ('uint8_t','uint16_t','uint32_t','uint64_t')[size - 1]
    ret.appstat(c.variable(field.name, type))
    f = ('enc_byte','enc_be16','enc_be32','enc_be64')[size - 1]
    for segment in field.custom_payload:
        size -= segment['size']
        if segment['name'] != '_unused':
            val = 'packet.' + segment['name']
            ret.appstat(field.name + ' |= ' + val + ' << ' + size)
    ret.appstat('dest = ' + str(c.fcall(f).add_param('dest', field.name)))
    return ret

#TODO: Nothing uses bitfields, but we should still implement this
def bitfield_dec(field):
    return c.linecomment('Decoder for bitfield: ' + str(field.name) + ' not yet implemented')

def bitfield_struct(field):
    ret = c.sequence()
    size = get_bitfield_size(field)
    type = ('uint8_t','uint16_t','uint32_t','uint64_t')[size - 1]
    for segment in field.custom_payload:
        if segment['name'] != '_unused':
            ret.appstat(c.variable(segment['name'], type))
    return ret

def handle_bitfield(field, op):
    return {
        'size': bitfield_size,
        'walk': bitfield_walk,
        'enc': bitfield_enc,
        'dec': bitfield_dec,
        'struct': bitfield_struct,
    }[op](field)

def option_size(field):
    opt_name = field.name + '_opt'
    ret = gen_sizer_inner((_field('bool', field.packet, opt_name),))
    body = c.block(None, 4, 'if(packet.' + opt_name + ')')
    return ret.append(body.append(gen_sizer_inner((_field(field.custom_payload, field.packet, field.name),))))

def option_walk(field):
    opt_name = field.name + '_opt'
    ret = gen_walker_inner((_field('bool', field.packet, opt_name, None, False, True),))
    body = c.block(None, 4, 'if(' + opt_name + ')')
    return ret.append(body.append(gen_walker_inner((_field(field.custom_payload, field.packet, field.name, None, field.final),))))

def option_enc(field):
    opt_name = field.name + '_opt'
    ret = gen_encoder_inner((_field('bool', field.packet, opt_name),))
    body = c.block(None, 4, 'if(source.' + opt_name + ')')
    return ret.append(body.append(gen_encoder_inner((_field(field.custom_payload, field.packet, field.name, None, field.final),))))

def option_dec(field):
    opt_name = field.name + '_opt'
    ret = gen_decoder_inner((_field('bool', field.packet, opt_name),))
    body = c.block(None, 4, 'if(dest->' + opt_name + ')')
    return ret.append(body.append(gen_decoder_inner((_field(field.custom_payload, field.packet, field.name, None, field.final),))))

def option_struct(field):
    fields = (
        _field('bool', field.packet, field.name + '_opt'),
        _field(field.custom_payload, field.packet, field.name),
    )
    return gen_struct_inner(fields)

def handle_option(field, op):
    return {
        'size': option_size,
        'walk': option_walk,
        'enc': option_enc,
        'dec': option_dec,
        'struct': option_struct,
    }[op](field)

def mapper_size(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def mapper_walk(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def mapper_enc(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def mapper_dec(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def mapper_struct(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def handle_mapper(field, op):
    return {
        'size': mapper_size,
        'walk': mapper_walk,
        'enc': mapper_enc,
        'dec': mapper_dec,
        'struct': mapper_struct,
    }[op](field)

def switch_size(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def switch_walk(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def switch_enc(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def switch_dec(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def switch_struct(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def handle_switch(field, op):
    return {
        'size': switch_size,
        'walk': switch_walk,
        'enc': switch_enc,
        'dec': switch_dec,
        'struct': switch_struct,
    }[op](field)

def array_size(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def array_walk(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def array_enc(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def array_dec(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def array_struct(field):
    return c.linecomment('Type for field: ' + str(field.name) + ' not yet implemented')

def handle_array(field, op):
    return {
        'size': array_size,
        'walk': array_walk,
        'enc': array_enc,
        'dec': array_dec,
        'struct': array_struct,
    }[op](field)

def particledata_size(field):
    return c.statement('size += ' + str(
        c.fcall('size_particledata').add_param('packet.' + field.name)
    ))

def particledata_walk(field):
    ret = c.sequence()
    ret.appstat('if((ret = ' + str(
        c.fcall('walk_particledata').add_param('source').add_param('max_len'
        ).add_param(field.custom_payload['compareTo'])
    ) + ') < 0) return -1')
    ret.appstat('size += ret')
    return ret

def particledata_enc(field):
    return c.statement('dest = ' + str(c.fcall(
        'enc_particledata').add_param('dest').add_param('source.' + field.name)
    ))

def particledata_dec(field):
    return c.statement('source = ' + str(
        c.fcall('dec_particledata').add_param('&dest->' + field.name
        ).add_param('source').add_param('dest->' + field.custom_payload['compareTo'])
    ))

#In practice handled by type_name_map and gen_packet_structure, but implemented
#just in case I change that.
def particledata_struct(field):
    return c.statement(c.variable(field.name, 'mc_particle'))

def handle_particledata(field, op):
    return {
        'size': particledata_size,
        'walk': particledata_walk,
        'enc': particledata_enc,
        'dec': particledata_dec,
        'struct': particledata_struct,
    }[op](field)

custom_type_map = {
    'buffer': handle_buffer,
    'mapper': handle_mapper,
    'array': handle_array,
    'switch': handle_switch,
    'bitfield': handle_bitfield,
    'option': handle_option,
    'particledata': handle_particledata,
}

def gen_struct_inner(fields):
    body = c.sequence()
    for f in fields:
        if f.type in type_name_map:
            body.appstat(c.variable(
                f.name,
                type_name_map[f.type]
            ))
        elif f.type in custom_type_map:
            body.append(custom_type_map[f.type](f, 'struct'))
        elif f.type == 'void':
            continue
        else:
            print('Don\'t know how to generate struct for:', f.type)
    return body

def gen_packet_structure(hdr, packet):
    body = c.struct(None, packet.full_name + '_t', innerIndent=4)
    body.code = gen_struct_inner(packet.fields)
    hdr.code.appstat(body)

def size_preprocessor(fields):
    if not fields:
        return []
    new_fields = []
    grouped = _field('grouped', fields[0].packet, None, custom_payload=0)
    for f in fields:
        if f.type == 'bitfield':
            grouped.custom_payload += get_bitfield_size(f)
        elif f.complex:
            if grouped.custom_payload:
                new_fields.append(grouped)
                grouped = _field('grouped', grouped.packet, None, custom_payload=0)
            new_fields.append(f)
        else:
            grouped.custom_payload += numeric_sizes[numeric_type_map[f.type]]
    if grouped.custom_payload:
        grouped.final = True
        new_fields.append(grouped)
    return new_fields

def gen_walker_inner(fields):
    body = c.sequence()
    for f in size_preprocessor(fields):
        if f.switched_on:
            body.appstat(type_name_map[f.type] + ' ' + f.name)
            if f.type in numeric_type_map:
                t = numeric_type_map[f.type]
                size = str(numeric_sizes[t])
                body.appstat('if(max_len < ' + size + ') return -1')
                if f.type in cast_map:
                    body.appstat(decode_generic(
                        t, '(' + cast_map[f.type] + '*) &' + f.name
                    ))
                else:
                    body.appstat(decode_generic(
                        numeric_type_map[f.type], '&' + f.name
                    ))
                body.appstat('size += ' + size)
                body.appstat('max_len -= ' + size)
            else:
                body.appstat('if((ret = ' + str(
                    c.fcall('walk_' + complex_type_map[f.type]
                    ).add_param('source').add_param('max_len')
                ) + ') < 0) return -1')
                body.appstat(decode_generic(
                    complex_type_map[f.type], '&' + f.name
                ))
                body.appstat('max_len -= ret')
                body.appstat('size += ret')
        elif f.type == 'grouped':
            size = str(f.custom_payload)
            body.appstat('if(max_len < ' + size + ') return -1')
            body.appstat('size += ' + size)
            if not f.final:
                body.appstat('source += ' + size)
                body.appstat('max_len -= ' + size)
        elif f.type in complex_type_map:
            body.appstat('if((ret = ' + str(
                c.fcall('walk_' + complex_type_map[f.type]
                ).add_param('source').add_param('max_len')
            ) + ') < 0) return -1')
            if not f.final:
                body.appstat('max_len -= ret')
                body.appstat('source += ret')
            body.appstat('size += ret')
        elif f.type in custom_type_map:
            body.append(custom_type_map[f.type](f, 'walk'))
        else:
            print('Dont know how to handle type:', f.type, "in packet:", f.packet.name)
            continue
    return body

def gen_packet_walker(file, hdr, packet):
    func = c.function('walk_' + packet.full_name).add_arg(
        c.variable('source', 'char', pointer = 1)).add_arg(
        c.variable('max_len', 'size_t')
    )
    hdr.code.appstat(func)
    body = c.block(innerIndent = 4, head = func)
    body.appstat(str(c.variable('size')) + ' = 0')
    if packet.has_complex:
        body.appstat(str(c.variable('ret')))
    body.append(gen_walker_inner(packet.fields))
    body.appstat('return size')
    file.code.append(body)
    file.code.append(c.blank())

def gen_sizer_inner(fields):
    body = c.sequence()
    for f in size_preprocessor(fields):
        if f.type == 'grouped':
            body.appstat('size += ' + str(f.custom_payload))
        elif f.type in complex_type_map:
            body.appstat('size += ' +
                str(c.fcall('size_' + complex_type_map[f.type]).add_param(
                    'packet.' + f.name
                ))
            )
        elif f.type in custom_type_map:
            body.append(custom_type_map[f.type](f, 'size'))
        else:
            continue
    return body

def gen_packet_sizer(file, hdr, packet):
    func = c.function('size_' + packet.full_name, 'size_t').add_arg(
        c.variable('packet', packet.full_name + '_t')
    )
    hdr.code.appstat(func)
    body = c.block(innerIndent = 4, head = func)
    complex_fields = []
    numeric_size = 0
    for f in size_preprocessor(packet.fields):
        if f.type == 'grouped':
            numeric_size += f.custom_payload
        else:
            complex_fields.append(f)
    if complex_fields:
        body.appstat(str(c.variable('size', 'size_t')) + ' = ' + str(numeric_size))
        body.append(gen_sizer_inner(complex_fields))
        body.appstat('return size')
    else:
        body.appstat('return ' + str(numeric_size))
    file.code.append(body)
    file.code.append(c.blank())

def gen_encoder_inner(fields):
    body = c.sequence()
    for f in fields:
        ref_name = 'source.' + str(f.name)
        if f.type in numeric_type_map:
            body.appstat('dest = ' + str(c.fcall(
                 'enc_'+ numeric_type_map[f.type]).add_param(
                    'dest').add_param(ref_name)
            ))
        elif f.type in complex_type_map:
            body.appstat('dest = ' + str(c.fcall(
                 'enc_'+ complex_type_map[f.type]).add_param(
                    'dest').add_param(ref_name)
            ))
        elif f.type in custom_type_map:
            body.append(custom_type_map[f.type](f, 'enc'))
        else:
            continue
    return body

def gen_packet_encoder(file, hdr, packet):
    func = c.function('enc_' + packet.full_name, 'char', pointer = 1).add_arg(
        c.variable('dest', 'char', pointer = 1)).add_arg(
        c.variable('source', packet.full_name + '_t')
    )
    hdr.code.appstat(func)
    body = c.block(innerIndent=4, head = func)
    body.append(gen_encoder_inner(packet.fields))
    body.appstat('return dest')
    file.code.append(body)
    file.code.append(c.blank())

def gen_decoder_inner(fields):
    body = c.sequence()
    for f in fields:
        ref_name = 'dest->' + str(f.name)
        if f.type in numeric_type_map:
            if f.type in cast_map:
                body.appstat(decode_generic(
                    numeric_type_map[f.type], '(' + cast_map[f.type] + '*) &' + ref_name
                ))
            else:
                body.appstat(decode_generic(
                    numeric_type_map[f.type], '&' + ref_name
                ))
        elif f.type == 'entitymetadata':
            body.appstat('count = ' + str(
                c.fcall('count_metatags').add_param('source')
            ))
            body.appstat('source = ' + str(
                c.fcall('dec_metadata').add_param('&' + ref_name).add_param('source').add_param('count')
            ))
        elif f.type == 'varint' or f.type == 'varlong':
            body.appstat(decode_generic(complex_type_map[f.type], '&' + ref_name))
        elif f.type in complex_type_map:
            body.appstat('if(!(' + str(decode_generic(
                complex_type_map[f.type], '&' + ref_name
            )) + ')) return NULL')
        elif f.type in custom_type_map:
            body.append(custom_type_map[f.type](f, 'dec'))
        else:
            continue
    return body

def gen_packet_decoder(file, hdr, packet):
    func = c.function('dec_' + packet.full_name, 'char', pointer = 1).add_arg(
        c.variable('dest', packet.full_name + '_t', pointer = 1)).add_arg(
        c.variable('source', 'char', pointer = 1)
    )
    hdr.code.appstat(func)
    body = c.block(innerIndent = 4, head = func)
    if packet.has_metadata:
        body.appstat(c.variable('count', 'size_t'))
    body.append(gen_decoder_inner(packet.fields))
    body.appstat('return source')
    file.code.append(body)
    file.code.append(c.blank())

def gen_freer_inner(fields):
    ret = c.sequence()
    for f in fields:
        if f.type in malloc_types:
            ret.appstat(c.fcall('free_' + malloc_types[f.type]).add_param(
                'packet.' + f.name
            ))
    return ret

def gen_packet_freer(file, hdr, packet):
    func = c.function('free_' + packet.full_name, 'void').add_arg(
        c.variable('packet', packet.full_name + '_t')
    )
    hdr.code.appstat(func)
    body = c.block(innerIndent = 4, head = func)
    body.append(gen_freer_inner(packet.fields))
    file.code.append(body)
    file.code.append(c.blank())

class _field:
    def __init__(self, type, packet, name=None, custom_payload=None, final=False, switched_on = False):
        self.type = type
        self.name = name
        self.custom_payload = custom_payload
        self.final = final
        self.packet = packet
        self.switched_on = switched_on
        self.complex = (type not in numeric_type_map and type != 'grouped') or switched_on

    @property
    def anon(self):
        return self.name is None

    @property
    def has_custom(self):
        return not self.custom_payload is None

class _packet:
    def __init__(self, proto_state, direction, name, packet_data):
        self.name = name
        self.full_name = '_'.join((proto_state, direction.lower(), name))
        self.fields = []
        self.has_metadata = False
        self.has_complex = False
        self.has_malloc = False
        #We always ignore the initial container
        for field in packet_data[1]:
            if isinstance(field['type'], list):
                f = _field(
                    field['type'][0].lower(),
                    self,
                    to_snake_case(field.get('name')),
                    field['type'][1],
                )
            else:
                f = _field(
                    field['type'].lower(),
                    self,
                    to_snake_case(field.get('name')),
                )
            if f.type == 'entitymetadata':
                self.has_metadata = True
            elif f.type == 'switch' or f.type == 'particledata':
                switch_name = to_snake_case(f.custom_payload['compareTo'])
                f.custom_payload['compareTo'] = switch_name
                for switch in self.fields:
                    if switch.name == switch_name:
                        switch.switched_on = True
                        switch.complex = True
            if f.complex:
                self.has_complex = True
            if f.type in malloc_types:
                self.has_malloc = True
            self.fields.append(f)
        if(self.fields):
            self.fields[-1].final = True


def gen_handler(fil, hdr, packet):
    gen_packet_structure(hdr, packet)
    hdr.code.append(c.blank())
    gen_packet_walker(fil, hdr, packet)
    gen_packet_sizer(fil, hdr, packet)
    gen_packet_encoder(fil, hdr, packet)
    gen_packet_decoder(fil, hdr, packet)
    if packet.has_malloc:
        gen_packet_freer(fil, hdr, packet)
    hdr.code.append(c.blank())

def run(version):
    data = minecraft_data(version).protocol
    fil = c.cfile(version.replace('.', '_') + '_proto.c')
    hdr = c.hfile(version.replace('.', '_') + '_proto.h')
    comment = c.comment(
        "\n  This file was generated by mcd2c.py" +
        "\n  It should not be edited by hand.\n"
    )
    hdr.code.append(comment)
    hdr.code.append(c.blank())
    hdr.code.append(c.sysinclude('stddef.h'))
    hdr.code.append(c.include("datautils.h"))
    hdr.code.append(c.blank())
    fil.code.append(comment)
    fil.code.append(c.blank())
    fil.code.append(c.sysinclude('stdlib.h'))
    fil.code.append(c.sysinclude('string.h'))
    fil.code.append(c.include(hdr.path))
    fil.code.append(c.blank())
    for proto_state in proto_states:
        for direction in directions:
            #lol wtf
            packet_map = data[proto_state][direction]['types']['packet'][1][1]['type'][1]['fields']
            for name, id in packet_map.items():
                packet = _packet(proto_state, direction, name, data[proto_state][direction]['types'][id])
                gen_handler(fil, hdr, packet)
    out = open(fil.path, 'w')
    out.write(str(fil))
    out.close()
    out = open(hdr.path, 'w')
    out.write(str(hdr))
    out.close()

if __name__ == '__main__':
    import sys
    version = sys.argv[1]
    print('Generating version', version)
    run(version)
