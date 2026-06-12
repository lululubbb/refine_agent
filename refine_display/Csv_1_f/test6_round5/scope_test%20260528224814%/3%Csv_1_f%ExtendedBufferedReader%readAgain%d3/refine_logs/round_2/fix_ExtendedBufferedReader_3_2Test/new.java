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
    void testreadAgain_initialValue() throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testreadAgain_afterRead() throws Exception {
        reader.read(); // Simulate reading a character to change lastChar
        
        // Use reflection to set lastChar to a specific value
        var lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 'A'); // Set lastChar to 'A' (ASCII 65)

        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals('A', result);
    }

    @Test
    void testreadAgain_afterReset() throws Exception {
        reader.read(); // Simulate reading
        var lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, ExtendedBufferedReader.UNDEFINED); // Reset lastChar to UNDEFINED

        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testreadAgain_boundaryValue() throws Exception {
        // Test the boundary condition by reading from an empty input
        ExtendedBufferedReader emptyReader = new ExtendedBufferedReader(new StringReader(""));
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(emptyReader);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testreadAgain_afterMultipleReads() throws Exception {
        reader.read(); // Simulate reading a character
        reader.read(); // Read again to change lastChar
        var lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 'B'); // Set lastChar to 'B' (ASCII 66)

        Method method = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        method.setAccessible(true);
        int result = (int) method.invoke(reader);
        Assertions.assertEquals('B', result);
    }
}