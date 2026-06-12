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
}