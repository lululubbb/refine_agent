package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_6_2Test {

    @Test
    void testLookAhead_normalCase() throws Exception {
        Reader reader = new StringReader("Hello");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        int result = invokeLookAhead(ebr);
        Assertions.assertEquals('H', result);
    }

    @Test
    void testLookAhead_multipleCharacters() throws Exception {
        Reader reader = new StringReader("World");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        // Look ahead should return 'W' without consuming it
        int result = invokeLookAhead(ebr);
        Assertions.assertEquals('W', result);
        
        // Ensure the first character is still available
        Assertions.assertEquals('W', ebr.read());
    }

    @Test
    void testLookAhead_endOfStream() throws Exception {
        Reader reader = new StringReader("A");
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        ebr.read(); // Consume the first character

        int result = invokeLookAhead(ebr);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    private int invokeLookAhead(ExtendedBufferedReader ebr) throws Exception {
        java.lang.reflect.Method method = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        method.setAccessible(true);
        return (int) method.invoke(ebr);
    }
}