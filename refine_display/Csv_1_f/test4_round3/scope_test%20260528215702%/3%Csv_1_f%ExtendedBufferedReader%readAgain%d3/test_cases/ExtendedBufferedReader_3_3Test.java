package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_3_3Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader("Test input"));
    }

    @Test
    void testreadAgain_initialValue() throws Exception {
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, -2); // Setting to UNDEFINED
        Assertions.assertEquals(-2, reader.readAgain());
    }

    @Test
    void testreadAgain_afterReading() throws Exception {
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 65); // Setting to a valid character (e.g., 'A')
        Assertions.assertEquals(65, reader.readAgain());
    }

    @Test
    void testreadAgain_afterStreamEnd() throws Exception {
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, -1); // Setting to END_OF_STREAM
        Assertions.assertEquals(-1, reader.readAgain());
    }

    @Test
    void testRead() throws Exception {
        int result = reader.read();
        Assertions.assertEquals('T', result); // Expecting 'T' from "Test input"
    }

    @Test
    void testReadWithBuffer() throws Exception {
        char[] buf = new char[4];
        int result = reader.read(buf, 0, 4);
        Assertions.assertEquals(4, result); // Expecting to read 4 characters
        Assertions.assertEquals("Test", new String(buf)); // Expecting "Test"
    }

    @Test
    void testReadLine() throws Exception {
        String result = reader.readLine();
        Assertions.assertEquals("Test input", result); // Expecting the full line
    }

    @Test
    void testLookAhead() throws Exception {
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 'T'); // Setting to 'T'
        int result = reader.lookAhead();
        Assertions.assertEquals('T', result); // Expecting to look ahead at 'T'
    }

    @Test
    void testGetLineNumber() throws Exception {
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        lineCounterField.setInt(reader, 1); // Setting line number to 1
        int result = reader.getLineNumber();
        Assertions.assertEquals(1, result); // Expecting line number 1
    }
}