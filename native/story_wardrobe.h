#pragma once
#include "story_wardrobe_profile.h"
#include "wardrobe_config.h"
#include "owned_action_array_copy.h"
namespace e33_story_wardrobe {
constexpr uint32_t operation=268,rejected=4370,uncertain=4371;
struct Array{uint64_t data=0;int32_t length=0,capacity=0;};
#pragma pack(push,1)
struct Packet{uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;CallIdentity ids[count]{};uint64_t leases[count]{};uint32_t guid[4]{},mode=0;uint32_t diagnostics[4]{};e33_wardrobe_config::Profile profile{};uint8_t tail[20984-24-count*24-20-16-2616]{};};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984);
struct Dispatcher{
 uint64_t base=0,session=0,owner=0;DWORD thread=0;CallIdentity ids[count]{};uint64_t leases[count]{};uint32_t guid[4]{};
 bool unknown=false,building=false,available=true;unsigned hooks=0,routes=0;uint32_t previews=0,selections=0,lists=0,stage=0;
 inline static Dispatcher*live=nullptr;
 e33_wardrobe_config::Profile profile{};
 static constexpr unsigned hooked[]={get_child,ordered,load,char_enum,load_anims,default_loaded,skin_completed,portrait_get,portrait_big,item_data};
 struct Held{CallIdentity id{};uint64_t lease=0;};
 Held current_scene{},preview{},owned[32]{};unsigned owned_count=0;uint64_t character_name=0,template_name=0;
 void*pool_pointer=nullptr;bool(*retain)(Dispatcher*,Held&,uint64_t)=nullptr;bool(*release)(Dispatcher*,Held&)=nullptr;
 struct Pending{unsigned input=0;uint64_t output=0,actor=0;};Pending pending[16]{};unsigned depth=0;uint8_t default_icon[40]{};uint64_t default_skin_name=0,default_face_name=0;
 bool belongs_to_save(uint64_t object)const{for(unsigned n=0;object&&n<32;++n,object=local_read<uint64_t>(object+32)){if(!call_capture(base,object).address)return false;if(object==ids[gi].address)return true;}return false;}
 void correct_default_icon(uint64_t value){
  const auto name=local_read<uint64_t>(value);if(name!=default_skin_name&&name!=default_face_name)return;
  // Only replace the native missing-item fallback. Returned value owns no
  // subpath allocation, and no inventory/character/save data is modified.
  if(!picto_struct_field(base,ids[item_struct].address,"Item_Icon_95_4D742A7E46F761161F9173969C69F468","SoftObjectProperty",32,40))throw uncertain;
  const auto at=value+32;
  if(!exact_name(base,at+8,"/Game/Gameplay/Inventory/Data/T_Inventory_MissingItem")&&!exact_name(base,at+8,"None"))return;
  const uint8_t empty[16]{};if(std::memcmp(reinterpret_cast<void*>(at+24),empty,16))throw uncertain;
  std::memcpy(reinterpret_cast<void*>(at),default_icon,40);
 }
 bool active()const{return owner||hooks||routes;}
 bool protects(uint64_t token)const{if(!active())return false;for(auto v:leases)if(v==token)return true;return false;}
 bool bound()const{e33_story_action::Dispatcher p;p.base=base;p.gi=ids[gi];std::memcpy(p.guid,guid,16);return thread==GetCurrentThreadId()&&p.bound();}
 bool is(uint64_t object,unsigned type)const{return object&&call_capture(base,object).address&&!(local_read<uint32_t>(object+8)&0x40018030U)&&call_derives(base,local_read<uint64_t>(object+16),ids[type].address);}
 bool menu(uint64_t object)const{e33_dialogue_text::Dispatcher h;const auto w=h.world(base,object);return is(object,scene)&&w&&zone_ref(base,w,"OwningGameInstance")==ids[gi].address;}
 uint64_t character()const{e33_inventory_reward::Dispatcher helper;uint64_t data=0;return helper.map_object(base,ids[gi].address,"CharactersCollection",2344,character_name,data)&&exact_name(base,data+48,profile.character)?data:0;}
 void call(uint64_t receiver,unsigned fn,void*args){if(!call_capture(base,receiver).address)throw uncertain;const auto pe=local_read<uint64_t>(local_read<uint64_t>(receiver)+0x268);if(pe!=base+0x1393330&&pe!=base+0x332bb90)throw uncertain;reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(receiver),reinterpret_cast<void*>(ids[fn].address),args);}
 template<class T>static void put(void*at,size_t offset,const T&value){std::memcpy(static_cast<uint8_t*>(at)+offset,&value,sizeof(value));}
 uint64_t prop(uint64_t object,const char*name,const char*kind,int offset,int size)const{for(auto cls=local_read<uint64_t>(object+16),n=uint64_t(0);cls&&n<32;++n,cls=local_read<uint64_t>(cls+0x40)){const auto p=picto_struct_field(base,cls,name,kind,offset,size);if(p)return p;}return 0;}
 bool array_valid(Array a,int limit=64)const{return a.length>=0&&a.length<=limit&&a.capacity>=a.length&&a.capacity<=4096&&(!a.capacity||a.data)&&(!a.data||!(a.data&7));}
 void copy_array(uint64_t field,uint64_t destination,const Array&value,const char*inner_kind){
  const auto inner=field?local_read<uint64_t>(field+0x78):0;
  if(!field||local_read<uint64_t>(field)!=base+e33_action_clone::array_property_table||(local_read<uint8_t>(field+0x70)&1)||!inner||local_read<uint64_t>(inner+16)!=field||local_read<int32_t>(inner+0x34)!=8||!exact_name(base,local_read<uint64_t>(inner+8),inner_kind)||!array_valid(value))throw uncertain;
  const auto previous_array=local_read<Array>(destination);if(!array_valid(previous_array))throw uncertain;
  using Copy=void(*)(void*,void*,const void*,int);reinterpret_cast<Copy>(base+e33_action_clone::array_copy_entry)(reinterpret_cast<void*>(field),reinterpret_cast<void*>(destination),&value,1);
  const auto actual=local_read<Array>(destination);if(!array_valid(actual)||actual.length!=value.length||(value.length&&actual.data==value.data))throw uncertain;
 }
 uint64_t output(uint64_t frame,unsigned input,const char*name,const char*kind,int offset,int size){
  const auto property=picto_struct_field(base,ids[input].address,name,kind,offset,size);if(!property)throw uncertain;
  for(auto out=local_read<uint64_t>(frame+0x80),n=uint64_t(0);out&&n<16;++n,out=local_read<uint64_t>(out+16))if(local_read<uint64_t>(out)==property){const auto address=local_read<uint64_t>(out+8);if(address<0x10000)throw uncertain;return address;}
  // Blueprint out values must use the caller's FOutParmRec, never locals.
  throw uncertain;
 }
 void tags(uint64_t object,const uint64_t*names,unsigned length){const auto p=prop(object,"ComponentTags","ArrayProperty",96,16);copy_array(p,object+96,{reinterpret_cast<uint64_t>(names),int(length),int(length)},"NameProperty");}
 bool has_tag(uint64_t object,uint64_t name)const{if(!prop(object,"ComponentTags","ArrayProperty",96,16))return false;const auto a=local_read<Array>(object+96);if(!array_valid(a))return false;for(int i=0;i<a.length;++i)if(local_read<uint64_t>(a.data+uint64_t(i)*8)==name)return true;return false;}
 uint64_t create(uint64_t actor,uint64_t cls,const double*transform){
  if(owned_count>=32)throw uncertain;alignas(16)uint8_t args[128]{};put(args,0,cls);args[8]=0;const double unit[12]={0,0,0,1,0,0,0,0,1,1,1,0};std::memcpy(args+16,unit,96);call(actor,add,args);
  const auto result=local_read<uint64_t>(reinterpret_cast<uint64_t>(args+120));if(!result||!retain(this,owned[owned_count],result))throw uncertain;++owned_count;
  alignas(16)uint8_t move[368]{};std::memcpy(move,transform,96);move[352]=1;call(result,set_world,move);return result;
 }
 uint64_t animation_class(uint64_t object)const{
  for(auto cls=local_read<uint64_t>(object+16),n=uint64_t(0);cls&&n<32;++n,cls=local_read<uint64_t>(cls+0x40))
   for(auto f=local_read<uint64_t>(cls+0x50),k=uint64_t(0);f&&k<512;++k,f=local_read<uint64_t>(f+0x18))
    if(exact_name(base,f+0x20,"AnimClass")){const auto off=local_read<int32_t>(f+0x44);
     if(local_read<uint64_t>(f+0x10)!=(cls|1)||!exact_name(base,local_read<uint64_t>(f+8),"ClassProperty")||local_read<int32_t>(f+0x34)!=8||off<40||off+8>local_read<int32_t>(cls+0x58))throw uncertain;
     return local_read<uint64_t>(object+uint64_t(off));}
  throw uncertain;
 }
 void set_animations(){if(!call_identity(base,preview.id))return;const auto actor=preview.id.address;
  const auto body=zone_ref(base,actor,"Body");if(!body)throw uncertain;
  uint64_t a=ids[body_anim].address;if(animation_class(body)!=a)call(body,set_anim,&a);
  // AssetAssign creates its own face component, not Actor.Face. Bind the
  // configured facial mesh after assignment, while it is owned by this
  // retained private preview. The gameplay NPC ABP deforms cinematic faces.
  alignas(16)uint8_t args[32]{};put(args,0,ids[skeletal].address);call(actor,components,args);
  const auto meshes=local_read<Array>(reinterpret_cast<uint64_t>(args+8));if(!array_valid(meshes,32))throw uncertain;
  uint64_t facial=0;
  for(int i=0;i<meshes.length;++i){const auto item=local_read<uint64_t>(meshes.data+uint64_t(i)*8);if(is(item,skeletal)&&prop(item,"SkeletalMesh","ObjectProperty",1368,8)&&local_read<uint64_t>(item+1368)==ids[face_mesh].address){if(facial)throw uncertain;facial=item;}}
  if(meshes.data)reinterpret_cast<void(__fastcall*)(void*)>(base+0x107c7d0)(reinterpret_cast<void*>(meshes.data));
  if(facial){a=ids[face_anim].address;if(animation_class(facial)!=a)call(facial,set_anim,&a);
   // Keep shared neck/shoulder bones aligned while the follower ticks its
   // unmatched facial bones. The engine skips unchanged leader bindings.
   alignas(16)uint8_t follow[16]{};put(follow,0,body);follow[9]=1;call(facial,leader_pose,follow);
  }
  const auto weapon=zone_ref(base,actor,"Weapons");if(weapon){uint8_t hide=1;call(weapon,set_hidden,&hide);}
 }
 void apply_saved_appearance(){
  if(!call_identity(base,preview.id))return;const auto data=character();
  const auto skin_component=zone_ref(base,preview.id.address,"BP_CinematicCharacterSkinComponent");
  if(!data||!is(skin_component,skin)||!prop(data,"CharacterCustomization","StructProperty",1992,80))throw uncertain;
  uint64_t assignment_name=0;if(!e33_blueprint_names::resolve(base,"Default",assignment_name))throw uncertain;alignas(16)uint8_t appearance[96]{};put(appearance,0,assignment_name);std::memcpy(appearance+8,reinterpret_cast<void*>(data+1992),80);
  call(skin_component,customize,appearance);
 }
 void clear_scene(bool destroy_components){
  if(destroy_components&&call_identity(base,current_scene.id)&&menu(current_scene.id.address)){
   // Rebuild the original menu map after removing our getters. This clears
   // references to the private child before that component is destroyed.
   uint64_t descriptor=0;const auto map=picto_field(base,ids[gi].address,"CharactersCollection","MapProperty",2344,80,&descriptor);
   e33_inventory_reward::Dispatcher schema;PictoSparseView view{};uint64_t values[32]{};unsigned length=0;
   if(!map||!schema.map_schema(base,descriptor,"ObjectProperty",8,24)||!picto_sparse(map,24,32,view))throw uncertain;
   for(int i=0;i<view.count;++i)if(view.active(i)){const auto at=view.data+uint64_t(i)*24,value=local_read<uint64_t>(at+8);if(local_read<uint64_t>(at)==character_name)continue;if(!call_capture(base,value).address||length>=32)throw uncertain;values[length++]=value;}
   Array roster{reinterpret_cast<uint64_t>(values),int(length),int(length)};call(current_scene.id.address,load,&roster);
  }
  if(destroy_components&&call_identity(base,current_scene.id)&&menu(current_scene.id.address))for(unsigned i=owned_count;i>0;--i)if(call_identity(base,owned[i-1].id)){uint64_t actor=current_scene.id.address;call(owned[i-1].id.address,destroy,&actor);}
  for(unsigned i=0;i<owned_count;++i)if(!release(this,owned[i]))throw uncertain;owned_count=0;
  if(!release(this,preview)||!release(this,current_scene))throw uncertain;
 }
 void prepare_scene(uint64_t actor){
  if(call_identity(base,current_scene.id)&&current_scene.id.address==actor&&call_identity(base,preview.id))return;
  if(building)throw uncertain;building=true;stage=10;
  if(current_scene.lease)clear_scene(false);
  if(!retain(this,current_scene,actor))throw uncertain;
  const auto source=zone_ref(base,actor,profile.template_component);if(!is(source,child))throw uncertain;
  alignas(16)double transform[12]{};call(source,world_transform,transform);
  // Apply the configured offset in the template component's local axes.
  const double x=transform[0],y=transform[1],z=transform[2],w=transform[3];
  alignas(16)double anchor_transform[12]{};
  const auto anchor=zone_ref(base,actor,profile.anchor_component);if(!is(anchor,child))throw uncertain;
  call(anchor,world_transform,anchor_transform);
  const auto*o=profile.party_offset;
  const double delta[3]={anchor_transform[4]+o[0]*(1-2*(y*y+z*z))+o[1]*2*(x*y-w*z)+o[2]*2*(x*z+w*y)-transform[4],anchor_transform[5]+o[0]*2*(x*y+w*z)+o[1]*(1-2*(x*x+z*z))+o[2]*2*(y*z-w*x)-transform[5],anchor_transform[6]+o[0]*2*(x*z-w*y)+o[1]*2*(y*z+w*x)+o[2]*(1-2*(x*x+y*y))-transform[6]};
  for(unsigned i=0;i<3;++i)transform[4+i]+=delta[i];
  const double preview_position[3]={transform[4],transform[5],transform[6]};
  const auto component_value=create(actor,ids[child].address,transform);
  uint64_t child_tag=0;if(!e33_blueprint_names::resolve(base,"ChildActor",child_tag))throw uncertain;
  const uint64_t child_tags[]={character_name,child_tag};tags(component_value,child_tags,2);
  uint64_t cls=ids[preview_class].address;call(component_value,set_class,&cls);
  const auto child_actor=zone_ref(base,component_value,"ChildActor");if(!child_actor||!retain(this,preview,child_actor))throw uncertain;
  const auto skin_component=zone_ref(base,child_actor,"BP_CinematicCharacterSkinComponent");
  if(!is(skin_component,skin))throw uncertain;
  uint64_t name_field=0;
  for(auto type=local_read<uint64_t>(skin_component+16),n=uint64_t(0);type&&n<32&&!name_field;++n,type=local_read<uint64_t>(type+0x40))
   for(auto f=local_read<uint64_t>(type+0x50),k=uint64_t(0);f&&k<512;++k,f=local_read<uint64_t>(f+0x18))
    if(exact_name(base,f+0x20,"CharacterHardcodedName")&&local_read<uint64_t>(f+0x10)==(type|1)&&exact_name(base,local_read<uint64_t>(f+8),"NameProperty")&&local_read<int32_t>(f+0x34)==8){name_field=f;break;}
  if(!name_field)throw uncertain;
  const auto name_offset=local_read<uint32_t>(name_field+0x44);
  if(name_offset<160||name_offset>1024||(!exact_name(base,skin_component+name_offset,"None")&&local_read<uint64_t>(skin_component+name_offset)!=template_name))throw uncertain;
  put(reinterpret_cast<void*>(skin_component),name_offset,character_name);
  const auto data=character();
  if(!data||!prop(data,"CharacterCustomization","StructProperty",1992,80))throw uncertain;
  uint64_t assignment_name=0;if(!e33_blueprint_names::resolve(base,"Default",assignment_name))throw uncertain;alignas(16)uint8_t appearance[96]{};put(appearance,0,assignment_name);
  std::memcpy(appearance+8,reinterpret_cast<void*>(data+1992),80);
  call(skin_component,customize,appearance);
  uint8_t hidden=1;call(child_actor,set_hidden,&hidden);set_animations();stage=11;
  alignas(16)uint8_t args[32]{};put(args,0,ids[component].address);call(actor,components,args);const auto all=local_read<Array>(reinterpret_cast<uint64_t>(args+8));if(!array_valid(all,512))throw uncertain;
  // Clone only the configured anchor view/lighting components. Other actors and their
  // components are never moved or retagged. These additions belong to this scene.
  for(int i=0;i<all.length;++i){const auto source_component=local_read<uint64_t>(all.data+uint64_t(i)*8);uint64_t anchor_name=0;if(!e33_blueprint_names::resolve(base,profile.anchor_tag,anchor_name))throw uncertain;if(!has_tag(source_component,anchor_name))continue;
   const bool is_camera=is(source_component,camera),is_light=is(source_component,light);if(!is_camera&&!is_light)continue;
   call(source_component,world_transform,transform);for(unsigned axis=0;axis<3;++axis)transform[4+axis]+=preview_position[axis]-anchor_transform[4+axis];
   const auto duplicate=create(actor,local_read<uint64_t>(source_component+16),transform);
   const auto source_tags=local_read<Array>(source_component+96);uint64_t names[64]{};if(!array_valid(source_tags))throw uncertain;
   for(int j=0;j<source_tags.length;++j){names[j]=local_read<uint64_t>(source_tags.data+uint64_t(j)*8);if(names[j]==anchor_name)names[j]=character_name;}tags(duplicate,names,unsigned(source_tags.length));
   if(is_camera){
    for(const auto off:{2540,2552,2684,2688}){const unsigned bytes=off==2540?12U:off==2552?28U:4U;std::memcpy(reinterpret_cast<void*>(duplicate+uint64_t(off)),reinterpret_cast<void*>(source_component+uint64_t(off)),bytes);}
   }else{
    // Same-class light clones need their authored units/channels as well as
    // intensity. Engine defaults can make an otherwise correct preview dark.
    for(auto type=local_read<uint64_t>(source_component+16),n=uint64_t(0);type&&n<16;++n,type=local_read<uint64_t>(type+0x40)){
     if(e33_mesh::named(base,type,"SceneComponent","/Script/Engine"))break;
     for(auto f=local_read<uint64_t>(type+0x50),k=uint64_t(0);f&&k<512;++k,f=local_read<uint64_t>(f+0x18)){
      const auto off=local_read<int32_t>(f+0x44),width=local_read<int32_t>(f+0x34);
      if(local_read<uint64_t>(f+0x10)!=(type|1)||off<160||off>4096||width<1||width>8)continue;
      const auto kind=local_read<uint64_t>(f+8);
      bool pod=exact_name(base,kind,"FloatProperty")||exact_name(base,kind,"DoubleProperty")||exact_name(base,kind,"IntProperty")||exact_name(base,kind,"ByteProperty")||exact_name(base,kind,"EnumProperty")||exact_name(base,kind,"BoolProperty");
      if(exact_name(base,kind,"StructProperty"))pod=exact_name(base,f+0x20,"LightingChannels")||exact_name(base,f+0x20,"LightColor");
      if(pod)std::memcpy(reinterpret_cast<void*>(duplicate+uint64_t(off)),reinterpret_cast<void*>(source_component+uint64_t(off)),size_t(width));
     }
    }
    // Intensity is dispatched through the engine after registration. Inherit
    // cone/attenuation dimensions only where their reflected POD fields exist.
    for(const auto name:{"AttenuationRadius","InnerConeAngle","OuterConeAngle","SourceWidth","SourceHeight"}){
     uint64_t field=0;for(auto type=local_read<uint64_t>(source_component+16),n=uint64_t(0);type&&n<32&&!field;++n,type=local_read<uint64_t>(type+0x40))for(auto f=local_read<uint64_t>(type+0x50),k=uint64_t(0);f&&k<4096;++k,f=local_read<uint64_t>(f+0x18))if(exact_name(base,f+0x20,name)&&exact_name(base,local_read<uint64_t>(f+8),"FloatProperty")&&local_read<int32_t>(f+0x34)==4){field=f;break;}
     if(field){const auto off=local_read<uint32_t>(field+0x44);if(off<160||off>4096)throw uncertain;const auto v=local_read<float>(source_component+off);if(!std::isfinite(v))throw uncertain;put(reinterpret_cast<void*>(duplicate),off,v);}
    }
    // Intensity is a reflected LightComponent float; don't assume its offset.
    uint64_t field=0;for(auto type=local_read<uint64_t>(source_component+16),n=uint64_t(0);type&&n<32&&!field;++n,type=local_read<uint64_t>(type+0x40))for(auto f=local_read<uint64_t>(type+0x50),k=uint64_t(0);f&&k<4096;++k,f=local_read<uint64_t>(f+0x18))if(exact_name(base,f+0x20,"Intensity")&&exact_name(base,local_read<uint64_t>(f+8),"FloatProperty")){field=f;break;}
    if(!field)throw uncertain;float value=local_read<float>(source_component+local_read<uint32_t>(field+0x44));if(!std::isfinite(value)||value<0)throw uncertain;call(duplicate,intensity,&value);uint8_t visibility[2]{};call(duplicate,set_visibility,visibility);
   }
  }
  if(all.data)reinterpret_cast<void(__fastcall*)(void*)>(base+0x107c7d0)(reinterpret_cast<void*>(all.data));
  ++previews;building=false;stage=0;
 }
 e33_blueprint_transform::Decision begin(uint64_t fn,void*object,void*frame){
  if(!owner||unknown||!bound())return {};const auto actor=reinterpret_cast<uint64_t>(object),f=reinterpret_cast<uint64_t>(frame);
  if(!f||local_read<uint64_t>(f+0x10)!=fn||local_read<uint64_t>(f+0x18)!=actor)return {};
  unsigned input=count;for(auto i:hooked)if(ids[i].address==fn){input=i;break;}if(input==count)return {};
  const auto data=character();if(!data)return {};const auto locals=local_read<uint64_t>(f+0x28);if(!locals)return {};
  if(!available){if(input!=ordered||!menu(actor))return {};if(depth>=16)throw uncertain;pending[depth++]={input,output(f,input,"OrderedCharacters","ArrayProperty",0,16),actor};return {depth,false};}
  if(input==default_loaded||input==skin_completed){
   if(!call_identity(base,preview.id)||actor!=zone_ref(base,preview.id.address,"BP_CinematicCharacterSkinComponent")||!call_identity(base,current_scene.id))return {};
   if(depth>=16)throw uncertain;pending[depth++]={input,0,current_scene.id.address};return {depth,false};
  }
  if(input==portrait_get||input==portrait_big){
   if(actor!=data)return {};const auto destination=output(f,input,input==portrait_get?"CharacterIcon":"CharacterIconBig","ObjectProperty",0,8);
   put(reinterpret_cast<void*>(destination),0,ids[portrait].address);put(reinterpret_cast<void*>(locals),0,ids[portrait].address);return {0,true};
  }
  if(input==item_data){
   if(!is(actor,item_instance)||!belongs_to_save(actor))return {};if(depth>=16)throw uncertain;
   pending[depth++]={input,output(f,input,"ItemStaticData","StructProperty",0,304),actor};return {depth,false};
  }
  if(input==char_enum){if(local_read<uint64_t>(locals)!=character_name)return {};const auto destination=output(f,input,"ReturnValue","ByteProperty",16,1);*reinterpret_cast<uint8_t*>(destination)=7;put(reinterpret_cast<void*>(locals),16,uint8_t(7));++selections;return {0,true};}
  if(!menu(actor))return {};
  if(input==load||input==get_child||input==ordered)prepare_scene(actor);
  if(input==get_child){if(local_read<uint64_t>(locals)!=data)return {};const auto destination=output(f,input,"Value","ObjectProperty",8,8);put(reinterpret_cast<void*>(destination),0,owned[0].id.address);return {0,true};}
  if(depth>=16)throw uncertain;auto&pending_call=pending[depth++];pending_call={input,input==ordered?output(f,input,"OrderedCharacters","ArrayProperty",0,16):0,actor};return {depth,false};
 }
 void end(uint64_t token){if(!token||token!=depth||depth>16)throw uncertain;const auto p=pending[--depth];pending[depth]={};if(!bound())return;if(p.input==item_data){if(is(p.actor,item_instance)&&belongs_to_save(p.actor))correct_default_icon(p.output);return;}if(!menu(p.actor))return;
  if(p.input==ordered){const auto data=character();if(!data)return;const auto a=local_read<Array>(p.output);if(!array_valid(a,16))throw uncertain;uint64_t values[17]{};bool found=false;for(int i=0;i<a.length;++i){values[i]=local_read<uint64_t>(a.data+uint64_t(i)*8);if(values[i]==data)found=true;}if(!available){unsigned length=0;for(int i=0;i<a.length;++i)if(values[i]!=data)values[length++]=values[i];if(length!=unsigned(a.length)){const auto property=picto_struct_field(base,ids[ordered].address,"OrderedCharacters","ArrayProperty",0,16);copy_array(property,p.output,{reinterpret_cast<uint64_t>(values),int(length),int(length)},"ObjectProperty");++lists;}return;}if(!found){values[a.length]=data;const auto property=picto_struct_field(base,ids[ordered].address,"OrderedCharacters","ArrayProperty",0,16);copy_array(property,p.output,{reinterpret_cast<uint64_t>(values),a.length+1,a.length+1},"ObjectProperty");++lists;}}
  if(p.input==load_anims||p.input==load)set_animations();
  if(p.input==default_loaded){apply_saved_appearance();set_animations();}
  if(p.input==skin_completed)set_animations();
 }
 e33_blueprint_transform::Decision checked_begin(uint64_t fn,void*object,void*frame){try{return begin(fn,object,frame);}catch(...){unknown=true;return {};}}
 void checked_end(uint64_t token){try{end(token);}catch(...){unknown=true;}}
 static e33_blueprint_transform::Decision pre(void*ctx,uint64_t fn,void*object,void*frame){auto*self=static_cast<Dispatcher*>(ctx);__try{return self->checked_begin(fn,object,frame);}__except(EXCEPTION_EXECUTE_HANDLER){self->unknown=true;return {};}}
 static void post(void*ctx,uint64_t token){auto*self=static_cast<Dispatcher*>(ctx);__try{self->checked_end(token);}__except(EXCEPTION_EXECUTE_HANDLER){self->unknown=true;}}
 static void __fastcall wrapper(void*object,void*frame,void*result){auto*self=live;if(!self)return;const auto fn=local_read<uint64_t>(reinterpret_cast<uint64_t>(frame)+0x10);const auto d=pre(self,fn,object,frame);if(!d.skip)reinterpret_cast<e33_trace::Entry>(self->base+0x13937a0)(object,frame,result);else if(fn==self->ids[char_enum].address&&result)*static_cast<uint8_t*>(result)=7;if(d.token)post(self,d.token);}
 bool path(unsigned i)const{if(i==gi)return true;const std::string p(e33_wardrobe_config::path(profile,i,specs[i].path));const auto dot=p.find('.'),colon=p.find(':',dot);if(dot==std::string::npos)return false;const auto pkg=p.substr(0,dot),name=p.substr(dot+1,colon==std::string::npos?std::string::npos:colon-dot-1);return colon==std::string::npos?e33_mesh::named(base,ids[i].address,name.c_str(),pkg.c_str()):(exact_name(base,ids[i].address+24,p.substr(colon+1).c_str())&&e33_mesh::named(base,local_read<uint64_t>(ids[i].address+32),name.c_str(),pkg.c_str()));}
 bool close(){if(!active())return true;if(unknown||building||depth)return false;while(hooks){const auto fn=ids[hooked[hooks-1]].address;if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(fn+0xd8),reinterpret_cast<void*>(base+0x13937a0),reinterpret_cast<void*>(wrapper))!=reinterpret_cast<void*>(wrapper)){unknown=true;return false;}--hooks;}e33_blueprint_transform::detach(this);while(routes){if(!BlueprintDirectTrace::release_narrative(ids[hooked[routes-1]].address))return false;--routes;}try{clear_scene(bound());}catch(...){unknown=true;return false;}owner=0;live=nullptr;return true;}
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.mode>5||p.guid[0]!=0xe33c5701U||!e33_wardrobe_config::valid(p.profile)){p.error=rejected;return;}for(auto v:p.diagnostics)if(v){p.error=rejected;return;}for(auto v:p.tail)if(v){p.error=rejected;return;}
  if(p.mode){if(owner!=p.owner||session!=s||std::memcmp(ids,p.ids,sizeof(ids))||std::memcmp(leases,p.leases,sizeof(leases))||std::memcmp(guid,p.guid,16)||std::memcmp(&profile,&p.profile,sizeof(profile))){p.error=rejected;return;}if(p.mode==2){if(!close()){p.error=uncertain;return;}p.state=3;return;}if(p.mode==4||p.mode==5){if(unknown||building||depth){p.error=uncertain;return;}try{available=p.mode==5;if(bound()&&call_identity(base,preview.id)){uint8_t hidden=available?0:1;call(preview.id.address,set_hidden,&hidden);}}catch(...){unknown=true;p.error=uncertain;return;}}if(p.mode==3){if(unknown||building||depth){p.error=uncertain;return;}try{if(available&&bound()&&call_identity(base,current_scene.id)&&menu(current_scene.id.address))set_animations();}catch(...){unknown=true;p.error=uncertain;return;}}put(p.diagnostics,0,previews);put(p.diagnostics,4,selections);put(p.diagnostics,8,lists);put(p.diagnostics,12,stage);if(unknown){p.error=uncertain;return;}p.state=p.mode+1;return;}
  if(active()){p.error=rejected;return;}for(unsigned i=0;i<count;++i)if(!call_identity(b,p.ids[i])||!pool.owns_object(s,p.leases[i],p.ids[i].address)){p.error=rejected;return;}
  base=b;session=s;profile=p.profile;thread=GetCurrentThreadId();std::memcpy(ids,p.ids,sizeof(ids));std::memcpy(leases,p.leases,sizeof(leases));std::memcpy(guid,p.guid,16);
  if(!bound()||!picto_frame_source(base)){p.error=rejected;return;}for(unsigned i=1;i<count;++i)if(!path(i)){p.error=4372;return;}
  for(const auto&spec:functions){const auto fn=ids[spec.index].address;if(local_read<uint32_t>(fn+0xb0)!=spec.flags||local_read<uint16_t>(fn+0xb6)!=spec.size||local_read<uint16_t>(fn+0xb8)!=spec.ret||local_read<uint64_t>(fn+0xd8)!=base+spec.entry){p.error=4373;return;}}
  for(const auto&spec:properties)if(!picto_struct_field(base,ids[spec.index].address,spec.name,spec.kind,spec.offset,spec.size)){p.error=4374;return;}
  if(local_read<uint64_t>(base+e33_action_clone::array_property_table+0xf0)!=base+e33_action_clone::array_copy_entry||std::memcmp(reinterpret_cast<void*>(base+e33_action_clone::array_copy_entry),e33_action_clone::array_copy_prefix,sizeof(e33_action_clone::array_copy_prefix))||!e33_blueprint_names::resolve(base,profile.character,character_name)||!e33_blueprint_names::resolve(base,profile.template_character,template_name)){p.error=4374;return;}
  if(!e33_blueprint_names::resolve(base,profile.default_skin,default_skin_name)||!e33_blueprint_names::resolve(base,profile.default_face,default_face_name)){p.error=4374;return;}
  alignas(16)uint8_t soft[48]{};put(soft,0,ids[portrait].address);call(ids[soft_cdo].address,object_soft,soft);
  const uint8_t no_subpath[16]{};if(std::memcmp(soft+32,no_subpath,16)){p.error=4374;return;}std::memcpy(default_icon,soft+8,40);
  pool_pointer=&pool;retain=[](Dispatcher*self,Held&v,uint64_t object){v.id=call_capture(self->base,object);if(!v.id.address)return false;TargetStrongReferenceOps ops{self->base,v.id};return static_cast<Pool*>(self->pool_pointer)->acquire(ops,self->session,object,v.lease)==StrongLeaseResult::Ok&&stabilize_retained_identity(ops,v.id);};release=[](Dispatcher*self,Held&v){TargetStrongReferenceOps ops{self->base,{-1,0,0}};if(v.lease&&static_cast<Pool*>(self->pool_pointer)->release(ops,self->session,v.lease)!=StrongLeaseResult::Ok)return false;v={};return true;};
  available=true;owner=p.owner;HMODULE pinned=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(wrapper),&pinned)){p.error=rejected;return;}live=this;
  for(auto input:hooked){if(!BlueprintDirectTrace::retain_narrative(base,ids[input].address)||!e33_blueprint_transform::attach(this,ids[input].address,pre,post)){p.error=uncertain;unknown=true;return;}++routes;if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(ids[input].address+0xd8),reinterpret_cast<void*>(wrapper),reinterpret_cast<void*>(base+0x13937a0))!=reinterpret_cast<void*>(base+0x13937a0)){p.error=uncertain;unknown=true;return;}++hooks;}p.state=1;
 }
};
}







