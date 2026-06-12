package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_3_2Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader("Test input"));
    }

    @Test
    void testReadAgain_initialValue() throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testReadAgain_afterSingleRead() throws Exception {
        reader.read(); // Simulate reading a character
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals('T', result); // Assert the first character read
    }

    @Test
    void testReadAgain_afterResetToUndefined() throws Exception {
        reader.read(); // Simulate reading
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertNotEquals(ExtendedBufferedReader.UNDEFINED, result);
        
        // Reset lastChar to UNDEFINED
        var lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, ExtendedBufferedReader.UNDEFINED); 
        
        result = (int) method.invoke(reader);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testReadAgain_boundaryValue_emptyInput() throws Exception {
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(emptyReader);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testReadAgain_afterMultipleReads() throws Exception {
        reader.read(); // Simulate reading a character
        reader.read(); // Read again to change lastChar
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals('e', result); // Assert the second character read
        
        // Read another character to check the lastChar value
        reader.read();
        result = (int) method.invoke(reader);
        Assertions.assertEquals('s', result); // Assert the third character read
    }
}