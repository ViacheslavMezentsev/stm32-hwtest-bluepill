// Независимые временные векторы: границы, дребезг, удержание и переполнение.
#include "button.hpp"
#include <cassert>

int main()
{
    ButtonState state = {};
    state.update( true, 0 );
    state.update( true, 29 );
    assert( state.presses == 0 );
    state.update( false, 29 );
    state.update( true, 30 );
    state.update( true, 59 );
    assert( state.presses == 0 );
    state.update( true, 60 );
    assert( state.presses == 1 && state.stable );
    state.update( true, 1000 );
    assert( state.presses == 1 );
    state.update( false, 1001 );
    state.update( true, 1010 );
    state.update( true, 1040 );
    assert( state.presses == 1 );
    state.update( false, 1041 );
    state.update( false, 1071 );
    assert( !state.stable );
    state.update( true, 1080 );
    state.update( true, 1110 );
    assert( state.presses == 2 && state.stable );
    state = {};
    state.update( true, 0xfffffff0U );
    state.update( true, 13 );
    assert( state.presses == 0 );
    state.update( true, 14 );
    assert( state.presses == 1 );
}
