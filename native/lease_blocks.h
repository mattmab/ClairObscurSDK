#pragma once
#include <array>
#include <memory>
#include <new>
#include <cstddef>

// Growth allocates additional blocks, never relocates a published Entry or an
// engine holder. This also preserves references across reentrant registration.
template<class Entry,size_t Initial,size_t Maximum,size_t Block=64>
class LeaseBlocks {
    static_assert(Initial>0 && Initial<=Maximum && Maximum<=8192 && Block>0);
    std::array<Entry,Initial> initial_{};
    std::array<std::unique_ptr<Entry[]>,(Maximum-Initial+Block-1)/Block> extra_{};
    size_t capacity_=Initial,blocks_=0;
public:
    size_t capacity() const { return capacity_; }
    size_t bytes() const { return sizeof(initial_)+blocks_*Block*sizeof(Entry); }
    bool reserve(size_t required) {
        if(required>Maximum) return false;
        while(capacity_<required) {
            auto block=std::unique_ptr<Entry[]>(new(std::nothrow) Entry[Block]{});
            if(!block) return false;
            extra_[blocks_++]=std::move(block);
            capacity_=(Initial+blocks_*Block<Maximum) ? Initial+blocks_*Block : Maximum;
        }
        return true;
    }
    Entry& at(size_t index) { return index<Initial ? initial_[index] : extra_[(index-Initial)/Block][(index-Initial)%Block]; }
    const Entry& at(size_t index) const { return index<Initial ? initial_[index] : extra_[(index-Initial)/Block][(index-Initial)%Block]; }
    template<class Storage,class Value> struct Iterator {
        Storage* storage;size_t index;
        Value& operator*() const { return storage->at(index); }
        Iterator& operator++() { ++index;return *this; }
        bool operator!=(const Iterator& other) const { return index!=other.index; }
    };
    auto begin() { return Iterator<LeaseBlocks,Entry>{this,0}; }
    auto end() { return Iterator<LeaseBlocks,Entry>{this,capacity_}; }
    auto begin() const { return Iterator<const LeaseBlocks,const Entry>{this,0}; }
    auto end() const { return Iterator<const LeaseBlocks,const Entry>{this,capacity_}; }
};
