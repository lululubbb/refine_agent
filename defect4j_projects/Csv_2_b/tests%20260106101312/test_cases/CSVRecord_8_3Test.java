package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_8_3Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;
    private String comment;
    private long recordNumber;

    @BeforeEach
    public void setUp() {
        values = new String[] {"value1", "value2", "value3"};
        mapping = mock(Map.class);
        comment = "Test comment";
        recordNumber = 42L;
        csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    public void testValuesMethod() throws NoSuchMethodException, InvocationTargetException, IllegalAccessException {
        // Use reflection to access the package-private values() method
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);

        String[] returnedValues = (String[]) valuesMethod.invoke(csvRecord);

        assertNotNull(returnedValues);
        assertArrayEquals(values, returnedValues);
    }

    @Test
    @Timeout(8000)
    public void testValuesMethodWithEmptyArray() throws NoSuchMethodException, InvocationTargetException, IllegalAccessException {
        String[] emptyValues = new String[0];
        CSVRecord emptyRecord = new CSVRecord(emptyValues, mapping, null, 0L);

        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);

        String[] returnedValues = (String[]) valuesMethod.invoke(emptyRecord);

        assertNotNull(returnedValues);
        assertEquals(0, returnedValues.length);
    }
}