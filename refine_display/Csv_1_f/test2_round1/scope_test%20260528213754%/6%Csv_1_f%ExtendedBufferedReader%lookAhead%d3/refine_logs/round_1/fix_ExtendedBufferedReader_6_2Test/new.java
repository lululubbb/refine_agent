package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_6_2Test {

    @Test
    void testLookAhead_normalCase() throws Exception {
        String input = "Hello";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        int result = invokeLookAhead(ebr);

        Assertions.assertEquals('H', result);
    }

    @Test
    void testLookAhead_emptyInput() throws Exception {
        String input = "";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        int result = invokeLookAhead(ebr);

        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testLookAhead_endOfStream() throws Exception {
        String input = "A";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);

        invokeLookAhead(ebr); // Read the first character

        int result = invokeLookAhead(ebr); // Now we should be at the end

        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    private int invokeLookAhead(ExtendedBufferedReader ebr) throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        method.setAccessible(true);
        return (int) method.invoke(ebr);
    }
}