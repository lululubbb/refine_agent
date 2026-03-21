package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_2_4Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;
    private String comment;
    private long recordNumber;

    @BeforeEach
    void setUp() throws Exception {
        values = new String[] { "value0", "value1", "value2" };
        mapping = new HashMap<>();
        mapping.put("col0", 0);
        mapping.put("col1", 1);
        mapping.put("col2", 2);
        comment = "comment";
        recordNumber = 123L;

        // Use reflection to invoke the package-private constructor
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(
                String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        csvRecord = constructor.newInstance(values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    void testGetByIndex_ValidIndexes() {
        for (int i = 0; i < values.length; i++) {
            assertEquals(values[i], csvRecord.get(i));
        }
    }

    @Test
    @Timeout(8000)
    void testGetByIndex_IndexOutOfBounds_Negative() {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(-1));
    }

    @Test
    @Timeout(8000)
    void testGetByIndex_IndexOutOfBounds_TooLarge() {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(values.length));
    }

    @Test
    @Timeout(8000)
    void testPrivateValuesFieldNotNull() throws Exception {
        Field valuesField = CSVRecord.class.getDeclaredField("values");
        valuesField.setAccessible(true);
        Object fieldValue = valuesField.get(csvRecord);
        assertNotNull(fieldValue);
        assertTrue(fieldValue instanceof String[]);
        assertArrayEquals(values, (String[]) fieldValue);
    }

    @Test
    @Timeout(8000)
    void testInvokeGetPrivateMethodUsingReflection() throws Exception {
        Method getMethod = CSVRecord.class.getDeclaredMethod("get", int.class);
        getMethod.setAccessible(true);
        Object result = getMethod.invoke(csvRecord, 1);
        assertEquals("value1", result);
    }
}