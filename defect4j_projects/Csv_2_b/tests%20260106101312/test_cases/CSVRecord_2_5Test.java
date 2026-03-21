package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Field;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_2_5Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;

    @BeforeEach
    public void setUp() throws Exception {
        values = new String[] {"value0", "value1", "value2"};
        mapping = mock(Map.class);
        csvRecord = new CSVRecord(values, mapping, "comment", 123L);
    }

    @Test
    @Timeout(8000)
    public void testGetByIndex_ValidIndex() {
        for (int i = 0; i < values.length; i++) {
            assertEquals(values[i], csvRecord.get(i));
        }
    }

    @Test
    @Timeout(8000)
    public void testGetByIndex_IndexOutOfBounds_Negative() {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(-1));
    }

    @Test
    @Timeout(8000)
    public void testGetByIndex_IndexOutOfBounds_TooLarge() {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(values.length));
    }

    @Test
    @Timeout(8000)
    public void testGetPrivateValuesFieldUsingReflection() throws Exception {
        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        String[] reflectedValues = (String[]) valuesField.get(csvRecord);
        assertArrayEquals(values, reflectedValues);
    }
}