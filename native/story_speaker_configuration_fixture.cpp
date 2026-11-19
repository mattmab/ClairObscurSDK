#include "story_speaker_configuration.h"
#include <cassert>
#include <cstdio>
int main(){
 using namespace e33_story_speaker;
 Packet p;p.owner=1;p.speaker_lease=2;
 p.npc={1,1001,0x10000};p.speaker={2,1002,0x20000};p.system_cdo={3,1003,0x30000};p.setter={4,1004,0x40000};
 p.count=3;p.text[0]='A';p.text[1]='B';assert(valid(p));
 p.text[4]=1;assert(!valid(p));p.text[4]=0;
 p.text[0]=0xd800;assert(!valid(p));p.text[1]=0xdc00;assert(valid(p));
 p.text[0]='A';p.text[1]=0;assert(!valid(p));p.text[1]='B';
 p.speaker.serial=0;assert(!valid(p));p.speaker.serial=1002;
 p.speaker_lease=0;assert(!valid(p));p.speaker_lease=2;
 p.tail[19859]=1;assert(!valid(p));p.tail[19859]=0;
 p.count=capacity+1;assert(!valid(p));
 std::puts("Story speaker packet validation passed");
}
