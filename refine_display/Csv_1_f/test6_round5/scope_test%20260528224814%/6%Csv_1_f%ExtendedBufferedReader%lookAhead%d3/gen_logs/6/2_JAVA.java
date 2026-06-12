package org.apache.commons.csv;
import java.io.BufferedReader;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ExtendedBufferedReader_6_6Test {
    private ExtendedBufferedReader extendedBufferedReader;

    @BeforeEach
    void setUp() {
        Reader reader = new StringReader("Hello");
        extendedBufferedReader = new ExtendedBufferedReader(reader);
    }

    @Test
    void testLookAhead_normalCase() throws Exception {
        int result = invokeLookAhead();
        assertEquals('H', result);
    }

    @Test
    void testLookAhead_emptyStream() throws Exception {
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        int result = emptyReader.lookAhead();
        assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testLookAhead_afterRead() throws Exception {
        extendedBufferedReader.read(); // read 'H'
        int result = invokeLookAhead();
        assertEquals('e', result);
    }

    private int invokeLookAhead() throws Exception {
        var method = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        method.setAccessible(true);
        return (int) method.invoke(extendedBufferedReader);
    }
}