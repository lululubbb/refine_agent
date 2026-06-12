package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_3_3Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader("Test line"));
    }

    @Test
    void testReadAgain_initialValue() throws Exception {
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        int result = (int) readAgainMethod.invoke(reader);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testReadAgain_afterReading() throws Exception {
        // Simulating a read operation to change lastChar
        int firstChar = reader.read(); // This would set lastChar to a valid character
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        int result = (int) readAgainMethod.invoke(reader);
        Assertions.assertEquals(firstChar, result); // Assert that lastChar matches the first character read
    }

    @Test
    void testReadAgain_afterMultipleReads() throws Exception {
        // Reading multiple characters to check lastChar consistency
        reader.read(); // Read first character
        reader.read(); // Read second character
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        int result = (int) readAgainMethod.invoke(reader);
        Assertions.assertEquals('t', result); // Assert lastChar is the last character read (should be 't' from "Test line")
    }

    @Test
    void testReadAgain_endOfStream() throws Exception {
        // Read until the end of the stream
        reader.readLine(); // Read the entire line
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        int result = (int) readAgainMethod.invoke(reader);
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result); // No more characters should set lastChar to UNDEFINED
    }
}