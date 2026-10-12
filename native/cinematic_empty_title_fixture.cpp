#include "cinematic_empty_title.h"
#include <cassert>
#include <iostream>
using namespace e33_empty_title;
uint64_t next_address=0x100000;
uint64_t block(){auto at=next_address;next_address+=1024;for(unsigned i=0;i<1024;++i)memory[at+i]=0;return at;}
uint64_t object(const char* name,const char* package){auto at=block(),outer=block();identities[at]={static_cast<int32_t>(at/1024),1,at};fixture_names[at+24]=name;fixture_names[outer+24]=package;put(at+32,outer);return at;}
uint64_t prop(uint64_t owner,const char* name,uint32_t off,uint32_t size,uint64_t vt,uint64_t flags){auto p=block();put(p,vt);put(p+16,owner|1);put(p+48,uint32_t{1});put(p+52,size);put(p+56,flags);put(p+68,off);fixture_names[p+32]=name;fixture_fields[{owner,name}]=p;return p;}
uint64_t array_prop(uint64_t owner,const char* name,uint32_t off,uint64_t flags,const char* type_name,uint32_t size,bool obj,const char* package="/Script/MovieScene"){
 auto p=prop(owner,name,off,16,0x6e0de80,flags),child=block(),type=object(type_name,package);
 put(p+120,child);put(child,uint64_t{obj?0x6e11d38ULL:0x6e136a0ULL});put(child+16,p);put(child+48,uint32_t{1});put(child+52,size);put(child+112,type);put(type+88,size);return p;
}
int main(){
 put(0x9272d30,DWORD{1});
 auto sequence=object("LS_Title_BackAtCamp","/Game/Cinematics/Titles/SequenceTitles/LS_Title_BackAtCamp");
 auto cls=object("LevelSequence","/Script/LevelSequence"),scene=object("MovieScene_0",""),sc=object("MovieScene","/Script/MovieScene");
 put(sequence+16,cls);put(sequence+112,scene);put(scene+32,sequence);put(scene+16,sc);
 prop(cls,"MovieScene",112,8,0x6e11d38,0x11c001000080208ULL);
 const char* ns[]={"Spawnables","Possessables","ObjectBindings"};const char* ts[]={"MovieSceneSpawnable","MovieScenePossessable","MovieSceneBinding"};uint32_t sizes[]={240,128,48};
 for(unsigned i=0;i<3;++i)array_prop(sc,ns[i],96+i*16,i==2?0x40008000000200ULL:0x40000000000200ULL,ts[i],sizes[i],false);
 prop(sc,"CameraCutTrack",240,8,0x6e11d38,0x14e001000080208ULL);array_prop(sc,"Tracks",224,0x144008000000208ULL,"MovieSceneTrack",8,true);
 auto data=block();put(scene+224,Array{data,4,4});
 const char* cn[]={"MovieSceneFadeTrack","BP_WidgetSequencerTrack_C","BP_InteractiveMusicSequencerTrack_C","MovieSceneEventTrack"};
 const char* pk[]={"/Script/MovieSceneTracks","/Game/Gameplay/UI/Sequencer/BP_WidgetSequencerTrack","/Game/Gameplay/InteractiveMusic/Sequencer/BP_InteractiveMusicSequencerTrack","/Script/MovieSceneTracks"};
 uint64_t track=0,tc=0;
 for(unsigned i=0;i<4;++i){track=object("track","");tc=object(cn[i],pk[i]);put(track+16,tc);put(track+32,scene);put(data+i*8,track);}
 array_prop(tc,"Sections",176,0x144008000000208ULL,"MovieSceneSection",8,true);auto sections=block(),section=object("section",""),seccls=object("MovieSceneEventTriggerSection","/Script/MovieSceneTracks");
 put(track+176,Array{sections,1,1});put(sections,section);put(section+32,track);put(section+16,seccls);
 auto channel=prop(seccls,"EventChannel",248,248,0x6e136a0,0x10000000000000ULL),type=object("MovieSceneEventChannel","/Script/MovieSceneTracks");put(channel+112,type);put(type+88,uint32_t{248});
 auto times=array_prop(type,"KeyTimes",80,0x40000000000200ULL,"FrameNumber",4,false,"/Script/CoreUObject"),values=array_prop(type,"KeyValues",96,0x40000000000200ULL,"MovieSceneEvent",40,false,"/Script/MovieSceneTracks");put(type+80,times);put(times+24,values);
 const auto id=identities[sequence];assert(validate(0,id));
 put(section+328,Array{block(),1,1});assert(!validate(0,id));put(section+328,Array{});
 put(section+344,Array{0,-1,0});assert(!validate(0,id));put(section+344,Array{});
 put(values+68,uint32_t{8});assert(!validate(0,id));put(values+68,uint32_t{96});
 put(values+24,times);assert(!validate(0,id));put(values+24,uint64_t{0});
 put(times+112,uint8_t{1});assert(!validate(0,id));put(times+112,uint8_t{0});
 put(scene+96,Array{block(),1,1});assert(!validate(0,id));put(scene+96,Array{});
 put(scene+240,track);assert(!validate(0,id));put(scene+240,uint64_t{0});
 auto first=local_read<uint64_t>(data);put(data,track);assert(!validate(0,id));put(data,first);
 fixture_names[tc+24]="MovieSceneSubTrack";assert(!validate(0,id));fixture_names[tc+24]="MovieSceneEventTrack";
 put(track+176,Array{sections,2,2});assert(!validate(0,id));put(track+176,Array{sections,1,1});
 auto stale=id;++stale.serial;assert(!validate(0,stale));put(0x9272d30,DWORD{2});assert(!validate(0,id));put(0x9272d30,DWORD{1});
 assert(validate(0,id));std::cout<<"empty title fixtures passed\n";
}


