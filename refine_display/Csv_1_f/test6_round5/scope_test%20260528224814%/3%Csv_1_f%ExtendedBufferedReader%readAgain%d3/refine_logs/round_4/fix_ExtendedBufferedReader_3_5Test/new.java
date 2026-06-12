package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_3_5Test {

    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader("Sample line"));
    }

    @Test
    void testReadAgain_initialValue() throws Exception {
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, ExtendedBufferedReader.UNDEFINED);
        
        int result = reader.readAgain();
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result, "Expected lastChar to be UNDEFINED");
    }

    @Test
    void testReadAgain_afterSettingLastChar() throws Exception {
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 100); 
        
        int result = reader.readAgain();
        Assertions.assertEquals(100, result, "Expected lastChar to be 100");
    }

    @Test
    void testReadAgain_afterSettingLastCharToEndOfStream() throws Exception {
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, ExtendedBufferedReader.END_OF_STREAM);
        
        int result = reader.readAgain();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result, "Expected lastChar to be END_OF_STREAM");
    }

    @Test
    void testReadAgain_afterSettingLastCharToBoundaryValue() throws Exception {
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 0); 
        
        int result = reader.readAgain();
        Assertions.assertEquals(0, result, "Expected lastChar to be 0");
    }

    @Test
    void testReadAgain_afterSettingLastCharToNegativeBoundary() throws Exception {
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, -10); // Testing negative boundary value
        
        int result = reader.readAgain();
        Assertions.assertEquals(-10, result, "Expected lastChar to be -10");
    }
}