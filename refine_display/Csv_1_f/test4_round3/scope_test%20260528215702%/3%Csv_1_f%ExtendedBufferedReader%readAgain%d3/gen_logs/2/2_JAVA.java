package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_3_2Test {

    @Test
    void testReadAgain_initialState() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, -2); // Set to UNDEFINED
        
        int result = reader.readAgain();
        
        Assertions.assertEquals(-2, result);
    }

    @Test
    void testReadAgain_afterReading() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("test"));
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 116); // Set lastChar to 't'
        
        int result = reader.readAgain();
        
        Assertions.assertEquals(116, result);
    }

    @Test
    void testReadAgain_afterEndOfStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(""));
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, -1); // Set to END_OF_STREAM
        
        int result = reader.readAgain();
        
        Assertions.assertEquals(-1, result);
    }
}