package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

class ExtendedBufferedReader_3_1Test {
    private ExtendedBufferedReader reader;

    @BeforeEach
    void setUp() {
        reader = new ExtendedBufferedReader(new StringReader("Test line"));
    }

    @Test
    void testReadAgain_defaultValue() throws Exception {
        // Access the private field lastChar using reflection
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, ExtendedBufferedReader.UNDEFINED);

        // Call the readAgain method
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        int result = (int) readAgainMethod.invoke(reader);

        // Assert the default value
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testReadAgain_afterSettingLastChar() throws Exception {
        // Access the private field lastChar using reflection
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 5); // Set lastChar to a specific value

        // Call the readAgain method
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        int result = (int) readAgainMethod.invoke(reader);

        // Assert the value of lastChar
        Assertions.assertEquals(5, result);
    }

    @Test
    void testReadAgain_afterResettingLastChar() throws Exception {
        // Access the private field lastChar and set it to a specific value
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, 10); // Set lastChar to a specific value

        // Reset lastChar to UNDEFINED
        lastCharField.setInt(reader, ExtendedBufferedReader.UNDEFINED);

        // Call the readAgain method
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        int result = (int) readAgainMethod.invoke(reader);

        // Assert the reset value
        Assertions.assertEquals(ExtendedBufferedReader.UNDEFINED, result);
    }

    @Test
    void testReadAgain_boundaryValue() throws Exception {
        // Access the private field lastChar and set it to the END_OF_STREAM value
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, ExtendedBufferedReader.END_OF_STREAM); // Set lastChar to END_OF_STREAM

        // Call the readAgain method
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        int result = (int) readAgainMethod.invoke(reader);

        // Assert the boundary value
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testReadAgain_invalidValue() throws Exception {
        // Access the private field lastChar and set it to an invalid value
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        lastCharField.setInt(reader, Integer.MAX_VALUE); // Set lastChar to an invalid value

        // Call the readAgain method
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        int result = (int) readAgainMethod.invoke(reader);

        // Assert that the result is not equal to the invalid value
        Assertions.assertNotEquals(Integer.MAX_VALUE, result);
    }
}