package org.apache.commons.csv;
import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_6_1Test {

    @Test
    void testlookAhead_normalCase() throws Exception {
        String input = "Hello";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        int result = invokeLookAhead(ebr);
        
        Assertions.assertEquals('H', result);
    }

    @Test
    void testlookAhead_emptyStream() throws Exception {
        String input = "";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        int result = invokeLookAhead(ebr);
        
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testlookAhead_endOfStream() throws Exception {
        String input = "A";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        // Read the first character
        ebr.read();
        
        int result = invokeLookAhead(ebr);
        
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    private int invokeLookAhead(ExtendedBufferedReader ebr) throws Exception {
        java.lang.reflect.Method method = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        method.setAccessible(true);
        return (int) method.invoke(ebr);
    }
}