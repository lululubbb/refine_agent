package org.apache.commons.csv;
import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_6_2Test {

    @Test
    void testLookAhead_normalCase() throws Exception {
        String input = "Hello";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        int result = invokeLookAhead(reader);

        Assertions.assertEquals('H', result);
    }

    @Test
    void testLookAhead_emptyStream() throws Exception {
        String input = "";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        int result = invokeLookAhead(reader);

        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testLookAhead_endOfStream() throws Exception {
        String input = "A";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        // Read the first character
        reader.read();

        int result = invokeLookAhead(reader);

        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    private int invokeLookAhead(ExtendedBufferedReader reader) throws Exception {
        java.lang.reflect.Method method = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        method.setAccessible(true);
        return (int) method.invoke(reader);
    }
}