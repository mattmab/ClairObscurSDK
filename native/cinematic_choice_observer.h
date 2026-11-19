#pragma once
// A bounded journal observer: it may update its owner's choice index only.
// It never changes arguments, invokes the engine, or enters trace registration.
namespace e33_cinematic_choice {
inline void* owner=nullptr;
inline void(*observe)(void*,void*,void*)=nullptr;
inline void(*direction)(void*,void*,unsigned)=nullptr;
inline void entry(void*object,void*frame){if(owner&&observe)observe(owner,object,frame);}
}
